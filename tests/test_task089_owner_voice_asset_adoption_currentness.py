from __future__ import annotations

import base64
import builtins
import copy
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import socket
import sqlite3
import subprocess
import traceback

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task082_owner_voice_private_media_custody import (
    ArtifactClass,
    CurrentnessState,
    GenerationEventKind,
    PrivateMediaCustodyReceipt,
    PrivateMediaGenerationEvent,
    custody_staged_binding_sha256,
    derive_generation_currentness,
    Task082Reason,
)
from ai_video_production.task089_owner_voice_asset_adoption_currentness import (
    Task089AdoptionAssessment,
    Task089ContractError,
    Task089FixtureBundle,
    Task089Q2PairHandoff,
    assess_adoption_fixture,
    build_q2_pair_handoff_fixture,
    parse_fixture_bundle,
)
import ai_video_production.task089_owner_voice_asset_adoption_currentness as task089_module
import ai_video_production.task082_owner_voice_private_media_custody as task082_module

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "task089-owner-voice-asset-adoption-currentness.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name
TASK082_SCHEMA = ROOT / "schemas" / "task082-owner-voice-private-media-custody.schema.json"
T0 = "2026-09-14T00:00:00.000000Z"
T1 = "2026-09-14T00:01:00.000000Z"
T2 = "2026-09-14T00:02:00.000000Z"
T3 = "2026-09-14T00:03:00.000000Z"
T9 = "2026-09-14T00:09:00.000000Z"


def h(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("ascii")).hexdigest()


def validator(schema: dict[str, object]) -> Draft202012Validator:
    owner = json.loads(TASK082_SCHEMA.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=Registry().with_resource(owner["$id"], Resource.from_contents(owner)))


def own(kind: str, body: dict[str, object]) -> dict[str, object]:
    body["record_sha256"] = sha256_bytes(
        b"BAI:TASK089:NONLIVE:" + kind.encode("ascii") + b":V1\0"
        + canonical_json_bytes({k: v for k, v in body.items() if k != "record_sha256"})
    )
    return body


def common(kind: str, **fields: object) -> dict[str, object]:
    return {
        "record_type": kind,
        "schema_version": 1,
        "adapter_owner_task": "TASK-089",
        "canonical_asset_owner_task": "TASK-003",
        "fixture_only": True,
        "authority_created": False,
        "execution_authorized": False,
        "owner_port_contract_status": "NOT_BOUND",
        "private_media_effect_count": 0,
        "asset_adoption_count": 0,
        **fields,
        "record_sha256": None,
    }


def semantic_key(request: dict[str, object]) -> str:
    excluded = {
        "record_type", "schema_version", "adapter_owner_task", "canonical_asset_owner_task",
        "fixture_only", "authority_created", "execution_authorized", "owner_port_contract_status",
        "private_media_effect_count", "asset_adoption_count", "record_sha256",
        "adoption_operation_id", "semantic_key_sha256",
    }
    return sha256_bytes(b"BAI:TASK089:FIXTURE_ADOPTION_KEY:V1\0" + canonical_json_bytes({k: v for k, v in request.items() if k not in excluded}))


def bundle_digest(bundle: dict[str, object]) -> str:
    return sha256_bytes(b"BAI:TASK089:NONLIVE:Task089FixtureBundleV1:V1\0" + canonical_json_bytes({k: v for k, v in bundle.items() if k != "bundle_sha256"}))


def raw_bundle(*, outcome: str = "REGISTERED", observation: str = "SNAPSHOT", fixture_case: str = "fixture-raw", fixture_session: str = "fixture-session", grant_decision: str = "ALLOW", project_id: str = "fixture-project", grant_expires_at: str = T9) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    if observation == "UNRESOLVED":
        outcome = "COMPLETION_UNKNOWN"
    subject = own("Task089SubjectFixtureV1", common("Task089SubjectFixtureV1", fixture_case=fixture_case, project_id=project_id, production_job_id="JOB-00000000000000000000000000", project_revision=1, owner_subject_revision=1))
    grant = own("Task089PurposeGrantFixtureV1", common("Task089PurposeGrantFixtureV1", subject_sha256=subject["record_sha256"], scope="OWNER_VOICE_CAPTURE", operation="CAPTURE_RAW_PUBLISH", output_role="RAW_CAPTURE", decision=grant_decision, policy_revision=1, grant_revision=1, issued_at=T0, expires_at=grant_expires_at, q1_readback_sha256=None))
    producer = own("Task089ProducerOutputFixtureV1", common("Task089ProducerOutputFixtureV1", subject_sha256=subject["record_sha256"], grant_sha256=grant["record_sha256"], producer_task="TASK-047", producer_output_role="TASK047_RAW_CAPTURE_OUTPUT", asset_role="RAW_CAPTURE", producer_operation_id="OP-00000000000000000000000000", output_sequence=1, content_sha256=h("opaque-raw-bytes"), media={"format":"PCM_S16LE","sample_rate_hz":48000,"channels":1,"sample_count":48000}, upstream_producer_sha256=None, q1_readback_sha256=None))
    media_digest = sha256_bytes(b"BAI:TASK089:FIXTURE_MEDIA:V1\0" + canonical_json_bytes(producer["media"]))
    binding = custody_staged_binding_sha256(opaque_artifact_id="fixture.raw.1", logical_slot_ref="fixture.raw.slot", generation_revision=1, owner_subject_revision_sha256=subject["record_sha256"], purpose="CAPTURE_RAW_PUBLISH", artifact_class=ArtifactClass.RAW_CAPTURE, content_sha256=producer["content_sha256"], media_metadata_sha256=media_digest, opened_physical_identity_sha256=h("physical-raw"), cipher_backend_identity_sha256=h("cipher-raw"), consent_rights_revision_sha256=grant["record_sha256"], observed_at=T1, fresh_until=T9)
    event = PrivateMediaGenerationEvent.create(event_kind=GenerationEventKind.GENERATION_PUBLISHED, logical_slot_ref="fixture.raw.slot", artifact_class=ArtifactClass.RAW_CAPTURE, event_revision=1, predecessor_event_sha256=None, owner_subject_revision_sha256=subject["record_sha256"], purpose="CAPTURE_RAW_PUBLISH", consent_rights_revision_sha256=grant["record_sha256"], created_at=T0, observed_at=T1, fresh_until=T9, trusted_time_binding_sha256=h("trusted-time"), published_generation_revision=1, opaque_artifact_id="fixture.raw.1", custody_binding_sha256=binding, content_sha256=producer["content_sha256"], media_metadata_sha256=media_digest, opened_physical_identity_sha256=h("physical-raw"), cipher_backend_identity_sha256=h("cipher-raw"), target_generation_revision=None, target_publish_event_sha256=None, tombstone_decision_sha256=None)
    receipt = PrivateMediaCustodyReceipt.create(opaque_artifact_id="fixture.raw.1", logical_slot_ref="fixture.raw.slot", generation_revision=1, predecessor_receipt_sha256=None, custody_binding_sha256=binding, owner_subject_revision_sha256=subject["record_sha256"], purpose="CAPTURE_RAW_PUBLISH", artifact_class=ArtifactClass.RAW_CAPTURE, content_sha256=producer["content_sha256"], media_metadata_sha256=media_digest, opened_physical_identity_sha256=h("physical-raw"), cipher_backend_identity_sha256=h("cipher-raw"), consent_rights_revision_sha256=grant["record_sha256"], generation_event_sha256=event.event_sha256, event_head_sha256=event.event_sha256, observed_at=T1, fresh_until=T9)
    custody = own("Task089CustodyFixtureV1", common("Task089CustodyFixtureV1", producer_sha256=producer["record_sha256"], custody_receipt=receipt.as_dict(), generation_events=[event.as_dict()]))
    request = common("Task089AdoptionRequestFixtureV1", subject_sha256=subject["record_sha256"], producer_sha256=producer["record_sha256"], custody_sha256=custody["record_sha256"], grant_sha256=grant["record_sha256"], adoption_operation_id="OP-11111111111111111111111111", expected_registry_generation=0, predecessor_registration_sha256=None, semantic_key_sha256=None)
    request["semantic_key_sha256"] = semantic_key(request)
    request = own("Task089AdoptionRequestFixtureV1", request)
    snapshot = None if outcome != "REGISTERED" else {"asset_id":"ASSET-22222222222222222222222222","production_job_id":subject["production_job_id"],"asset_type":"AUDIO","asset_role":"RAW_CAPTURE","logical_uri":"asset://JOB-00000000000000000000000000/owner-voice/raw_capture/ASSET-22222222222222222222222222","checksum":producer["content_sha256"],"asset_version":1,"producer_operation_id":request["adoption_operation_id"],"custody_receipt_sha256":receipt.receipt_sha256}
    generation = 1 if outcome == "REGISTERED" else 0
    registration = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=request["record_sha256"], outcome=outcome, registry_generation=generation, asset_snapshot=snapshot))
    if observation == "SNAPSHOT":
        readback_fields = dict(registration_sha256=registration["record_sha256"], observed_subject_sha256=subject["record_sha256"], observed_grant_sha256=grant["record_sha256"], observed_registry_generation=1, selected_asset_id=snapshot["asset_id"], selected_registration_sha256=registration["record_sha256"], observed_custody_sha256=custody["record_sha256"])
    elif observation == "NO_WRITE":
        readback_fields = dict(registration_sha256=registration["record_sha256"], observed_subject_sha256=subject["record_sha256"], observed_grant_sha256=grant["record_sha256"], observed_registry_generation=0, selected_asset_id=None, selected_registration_sha256=None, observed_custody_sha256=custody["record_sha256"])
    elif observation == "UNRESOLVED":
        readback_fields = dict(registration_sha256=registration["record_sha256"], observed_subject_sha256=None, observed_grant_sha256=None, observed_registry_generation=generation, selected_asset_id=None, selected_registration_sha256=None, observed_custody_sha256=None)
    else:
        readback_fields = dict(registration_sha256=None, observed_subject_sha256=None, observed_grant_sha256=None, observed_registry_generation=None, selected_asset_id=None, selected_registration_sha256=None, observed_custody_sha256=None)
    readback = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=request["record_sha256"], observation_kind=observation, fixture_session=fixture_session, observed_at=T2, fresh_until=T9, **readback_fields))
    records = [subject, grant, producer, custody, request, readback] if observation in {"UNAVAILABLE", "RESTARTED"} else [subject, grant, producer, custody, request, registration, readback]
    bundle = {"record_type":"Task089FixtureBundleV1","schema_version":1,"fixture_case":fixture_case,"fixture_session":fixture_session,"observed_at":T2,"records":records,"fixture_only":True,"authority_created":False,"execution_authorized":False,"owner_port_contract_status":"NOT_BOUND","bundle_sha256":None}
    bundle["bundle_sha256"] = bundle_digest(bundle)
    return bundle, {"S":subject,"G":grant,"P":producer,"CU":custody,"R":request,"A":registration,"O":readback}


def later_raw_generation_bundle(*, prior_tombstone: bool = False) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    """Build a complete successor prefix without constructing a live Asset/store."""
    _, old = raw_bundle()
    subject, grant, producer1 = old["S"], old["G"], old["P"]
    event1 = PrivateMediaGenerationEvent.from_mapping(old["CU"]["generation_events"][0])
    events1: list[dict[str, object]] = [event1.as_dict()]
    predecessor = event1
    if prior_tombstone:
        tombstone = PrivateMediaGenerationEvent.create(
            event_kind=GenerationEventKind.GENERATION_REVOKED,
            logical_slot_ref=event1.logical_slot_ref,
            artifact_class=event1.artifact_class,
            event_revision=2,
            predecessor_event_sha256=event1.event_sha256,
            owner_subject_revision_sha256=event1.owner_subject_revision_sha256,
            purpose=event1.purpose,
            consent_rights_revision_sha256=event1.consent_rights_revision_sha256,
            created_at=T1,
            observed_at=T2,
            fresh_until=T9,
            trusted_time_binding_sha256=h("prior-tombstone-time"),
            published_generation_revision=None,
            opaque_artifact_id=None,
            custody_binding_sha256=None,
            content_sha256=None,
            media_metadata_sha256=None,
            opened_physical_identity_sha256=None,
            cipher_backend_identity_sha256=None,
            target_generation_revision=1,
            target_publish_event_sha256=event1.event_sha256,
            tombstone_decision_sha256=h("prior-tombstone-decision"),
        )
        events1.append(tombstone.as_dict())
        predecessor = tombstone
    custody1 = own("Task089CustodyFixtureV1", common("Task089CustodyFixtureV1", producer_sha256=producer1["record_sha256"], custody_receipt=old["CU"]["custody_receipt"], generation_events=events1))
    request1 = common("Task089AdoptionRequestFixtureV1", subject_sha256=subject["record_sha256"], producer_sha256=producer1["record_sha256"], custody_sha256=custody1["record_sha256"], grant_sha256=grant["record_sha256"], adoption_operation_id=old["R"]["adoption_operation_id"], expected_registry_generation=0, predecessor_registration_sha256=None, semantic_key_sha256=None)
    request1["semantic_key_sha256"] = semantic_key(request1)
    request1 = own("Task089AdoptionRequestFixtureV1", request1)
    snapshot1 = dict(old["A"]["asset_snapshot"])
    snapshot1["producer_operation_id"] = request1["adoption_operation_id"]
    registration1 = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=request1["record_sha256"], outcome="REGISTERED", registry_generation=1, asset_snapshot=snapshot1))
    producer2 = own("Task089ProducerOutputFixtureV1", common("Task089ProducerOutputFixtureV1", subject_sha256=subject["record_sha256"], grant_sha256=grant["record_sha256"], producer_task="TASK-047", producer_output_role="TASK047_RAW_CAPTURE_OUTPUT", asset_role="RAW_CAPTURE", producer_operation_id="OP-33333333333333333333333333", output_sequence=1, content_sha256=h("opaque-raw-generation-two"), media=producer1["media"], upstream_producer_sha256=None, q1_readback_sha256=None))
    metadata2 = sha256_bytes(b"BAI:TASK089:FIXTURE_MEDIA:V1\0" + canonical_json_bytes(producer2["media"]))
    binding2 = custody_staged_binding_sha256(opaque_artifact_id="fixture.raw.2", logical_slot_ref="fixture.raw.slot", generation_revision=2, owner_subject_revision_sha256=subject["record_sha256"], purpose="CAPTURE_RAW_PUBLISH", artifact_class=ArtifactClass.RAW_CAPTURE, content_sha256=producer2["content_sha256"], media_metadata_sha256=metadata2, opened_physical_identity_sha256=h("physical-raw-two"), cipher_backend_identity_sha256=h("cipher-raw-two"), consent_rights_revision_sha256=grant["record_sha256"], observed_at=T2, fresh_until=T9)
    event2 = PrivateMediaGenerationEvent.create(event_kind=GenerationEventKind.GENERATION_PUBLISHED, logical_slot_ref="fixture.raw.slot", artifact_class=ArtifactClass.RAW_CAPTURE, event_revision=len(events1) + 1, predecessor_event_sha256=predecessor.event_sha256, owner_subject_revision_sha256=subject["record_sha256"], purpose="CAPTURE_RAW_PUBLISH", consent_rights_revision_sha256=grant["record_sha256"], created_at=T2, observed_at=T2, fresh_until=T9, trusted_time_binding_sha256=h("generation-two-time"), published_generation_revision=2, opaque_artifact_id="fixture.raw.2", custody_binding_sha256=binding2, content_sha256=producer2["content_sha256"], media_metadata_sha256=metadata2, opened_physical_identity_sha256=h("physical-raw-two"), cipher_backend_identity_sha256=h("cipher-raw-two"), target_generation_revision=None, target_publish_event_sha256=None, tombstone_decision_sha256=None)
    receipt1 = PrivateMediaCustodyReceipt.from_mapping(custody1["custody_receipt"])
    receipt2 = PrivateMediaCustodyReceipt.create(opaque_artifact_id="fixture.raw.2", logical_slot_ref="fixture.raw.slot", generation_revision=2, predecessor_receipt_sha256=receipt1.receipt_sha256, custody_binding_sha256=binding2, owner_subject_revision_sha256=subject["record_sha256"], purpose="CAPTURE_RAW_PUBLISH", artifact_class=ArtifactClass.RAW_CAPTURE, content_sha256=producer2["content_sha256"], media_metadata_sha256=metadata2, opened_physical_identity_sha256=h("physical-raw-two"), cipher_backend_identity_sha256=h("cipher-raw-two"), consent_rights_revision_sha256=grant["record_sha256"], generation_event_sha256=event2.event_sha256, event_head_sha256=event2.event_sha256, observed_at=T2, fresh_until=T9)
    custody2 = own("Task089CustodyFixtureV1", common("Task089CustodyFixtureV1", producer_sha256=producer2["record_sha256"], custody_receipt=receipt2.as_dict(), generation_events=[*events1, event2.as_dict()]))
    request2 = common("Task089AdoptionRequestFixtureV1", subject_sha256=subject["record_sha256"], producer_sha256=producer2["record_sha256"], custody_sha256=custody2["record_sha256"], grant_sha256=grant["record_sha256"], adoption_operation_id="OP-44444444444444444444444444", expected_registry_generation=1, predecessor_registration_sha256=registration1["record_sha256"], semantic_key_sha256=None)
    request2["semantic_key_sha256"] = semantic_key(request2)
    request2 = own("Task089AdoptionRequestFixtureV1", request2)
    snapshot2 = {"asset_id":"ASSET-55555555555555555555555555","production_job_id":subject["production_job_id"],"asset_type":"AUDIO","asset_role":"RAW_CAPTURE","logical_uri":"asset://JOB-00000000000000000000000000/owner-voice/raw_capture/ASSET-55555555555555555555555555","checksum":producer2["content_sha256"],"asset_version":1,"producer_operation_id":request2["adoption_operation_id"],"custody_receipt_sha256":receipt2.receipt_sha256}
    registration2 = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=request2["record_sha256"], outcome="REGISTERED", registry_generation=2, asset_snapshot=snapshot2))
    readback2 = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=request2["record_sha256"], registration_sha256=registration2["record_sha256"], observation_kind="SNAPSHOT", observed_subject_sha256=subject["record_sha256"], observed_grant_sha256=grant["record_sha256"], observed_registry_generation=2, selected_asset_id=snapshot2["asset_id"], selected_registration_sha256=registration2["record_sha256"], observed_custody_sha256=custody2["record_sha256"], fixture_session="fixture-session", observed_at=T2, fresh_until=T9))
    records = [subject, grant, producer1, custody1, request1, registration1, producer2, custody2, request2, registration2, readback2]
    bundle = {"record_type":"Task089FixtureBundleV1","schema_version":1,"fixture_case":"fixture-raw","fixture_session":"fixture-session","observed_at":T2,"records":records,"fixture_only":True,"authority_created":False,"execution_authorized":False,"owner_port_contract_status":"NOT_BOUND","bundle_sha256":None}
    bundle["bundle_sha256"] = bundle_digest(bundle)
    return bundle, {"S":subject,"G":grant,"P1":producer1,"CU1":custody1,"R1":request1,"A1":registration1,"P2":producer2,"CU2":custody2,"R2":request2,"A2":registration2,"O2":readback2}


def rewire_successor_custody(payload: dict[str, object], records: dict[str, dict[str, object]], custody_body: dict[str, object]) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    """Keep own hashes intact so prefix failures reach the relation validator."""
    custody = own("Task089CustodyFixtureV1", custody_body)
    request = dict(records["R2"], custody_sha256=custody["record_sha256"], semantic_key_sha256=None)
    request["semantic_key_sha256"] = semantic_key(request)
    request = own("Task089AdoptionRequestFixtureV1", request)
    registration = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=request["record_sha256"], outcome="REGISTERED", registry_generation=2, asset_snapshot=records["A2"]["asset_snapshot"]))
    readback = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=request["record_sha256"], registration_sha256=registration["record_sha256"], observation_kind="SNAPSHOT", observed_subject_sha256=records["S"]["record_sha256"], observed_grant_sha256=records["G"]["record_sha256"], observed_registry_generation=2, selected_asset_id=records["A2"]["asset_snapshot"]["asset_id"], selected_registration_sha256=registration["record_sha256"], observed_custody_sha256=custody["record_sha256"], fixture_session="fixture-session", observed_at=T2, fresh_until=T9))
    replacement = {records["CU2"]["record_sha256"]:custody, records["R2"]["record_sha256"]:request, records["A2"]["record_sha256"]:registration, records["O2"]["record_sha256"]:readback}
    result = dict(payload)
    result["records"] = [replacement.get(record["record_sha256"], record) for record in payload["records"]]
    result["bundle_sha256"] = bundle_digest(result)
    return result, {**records, "CU2":custody, "R2":request, "A2":registration, "O2":readback}


def reseal_raw_publication(payload: dict[str, object], records: dict[str, dict[str, object]], *, event_updates: dict[str, object], receipt_overrides: dict[str, object] | None = None) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    """Causally reseal a one-generation raw graph without external helpers."""
    source = records["CU"]["generation_events"][0]
    event_fields = {key: value for key, value in source.items() if key not in {"record_type", "schema_version", "canonical_owner_task", "event_sha256"}}
    event_fields.update(event_updates)
    binding = custody_staged_binding_sha256(
        opaque_artifact_id=event_fields["opaque_artifact_id"], logical_slot_ref=event_fields["logical_slot_ref"], generation_revision=event_fields["published_generation_revision"], owner_subject_revision_sha256=event_fields["owner_subject_revision_sha256"], purpose=event_fields["purpose"], artifact_class=event_fields["artifact_class"], content_sha256=event_fields["content_sha256"], media_metadata_sha256=event_fields["media_metadata_sha256"], opened_physical_identity_sha256=event_fields["opened_physical_identity_sha256"], cipher_backend_identity_sha256=event_fields["cipher_backend_identity_sha256"], consent_rights_revision_sha256=event_fields["consent_rights_revision_sha256"], observed_at=event_fields["observed_at"], fresh_until=event_fields["fresh_until"],
    )
    event_fields["custody_binding_sha256"] = binding
    event = PrivateMediaGenerationEvent.create(**event_fields).as_dict()
    receipt_fields = {key: event[key] for key in ("opaque_artifact_id", "logical_slot_ref", "owner_subject_revision_sha256", "purpose", "artifact_class", "content_sha256", "media_metadata_sha256", "opened_physical_identity_sha256", "cipher_backend_identity_sha256", "consent_rights_revision_sha256", "observed_at", "fresh_until")}
    receipt_fields.update(generation_revision=event["published_generation_revision"], predecessor_receipt_sha256=None, custody_binding_sha256=event["custody_binding_sha256"], generation_event_sha256=event["event_sha256"], event_head_sha256=event["event_sha256"])
    if receipt_overrides:
        receipt_fields.update(receipt_overrides)
        receipt_fields["custody_binding_sha256"] = custody_staged_binding_sha256(
            opaque_artifact_id=receipt_fields["opaque_artifact_id"], logical_slot_ref=receipt_fields["logical_slot_ref"], generation_revision=receipt_fields["generation_revision"], owner_subject_revision_sha256=receipt_fields["owner_subject_revision_sha256"], purpose=receipt_fields["purpose"], artifact_class=receipt_fields["artifact_class"], content_sha256=receipt_fields["content_sha256"], media_metadata_sha256=receipt_fields["media_metadata_sha256"], opened_physical_identity_sha256=receipt_fields["opened_physical_identity_sha256"], cipher_backend_identity_sha256=receipt_fields["cipher_backend_identity_sha256"], consent_rights_revision_sha256=receipt_fields["consent_rights_revision_sha256"], observed_at=receipt_fields["observed_at"], fresh_until=receipt_fields["fresh_until"],
        )
    receipt = PrivateMediaCustodyReceipt.create(**receipt_fields).as_dict()
    custody = own("Task089CustodyFixtureV1", common("Task089CustodyFixtureV1", producer_sha256=records["P"]["record_sha256"], custody_receipt=receipt, generation_events=[event]))
    request = dict(records["R"], custody_sha256=custody["record_sha256"], semantic_key_sha256=None)
    request["semantic_key_sha256"] = semantic_key(request)
    request = own("Task089AdoptionRequestFixtureV1", request)
    snapshot = dict(records["A"]["asset_snapshot"], custody_receipt_sha256=receipt["receipt_sha256"])
    registration = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=request["record_sha256"], outcome="REGISTERED", registry_generation=1, asset_snapshot=snapshot))
    readback = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=request["record_sha256"], registration_sha256=registration["record_sha256"], observation_kind="SNAPSHOT", observed_subject_sha256=records["S"]["record_sha256"], observed_grant_sha256=records["G"]["record_sha256"], observed_registry_generation=1, selected_asset_id=snapshot["asset_id"], selected_registration_sha256=registration["record_sha256"], observed_custody_sha256=custody["record_sha256"], fixture_session="fixture-session", observed_at=T2, fresh_until=T9))
    result = dict(payload, records=[records["S"], records["G"], records["P"], custody, request, registration, readback])
    result["bundle_sha256"] = bundle_digest(result)
    return result, {**records, "CU":custody, "R":request, "A":registration, "O":readback}


def canonical_bundle() -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    _, raw = raw_bundle()
    subject, raw_grant, raw_producer = raw["S"], raw["G"], raw["P"]
    grant = own("Task089PurposeGrantFixtureV1", common("Task089PurposeGrantFixtureV1", subject_sha256=subject["record_sha256"], scope="OWNER_VOICE_CAPTURE", operation="CAPTURE_CANONICAL_PUBLISH", output_role="CANONICAL_PCM", decision="ALLOW", policy_revision=1, grant_revision=2, issued_at=T0, expires_at=T9, q1_readback_sha256=None))
    producer = own("Task089ProducerOutputFixtureV1", common("Task089ProducerOutputFixtureV1", subject_sha256=subject["record_sha256"], grant_sha256=grant["record_sha256"], producer_task="TASK-047", producer_output_role="TASK047_CANONICAL_PCM_OUTPUT", asset_role="CANONICAL_PCM", producer_operation_id="OP-55555555555555555555555555", output_sequence=1, content_sha256=h("opaque-canonical-bytes"), media={"format":"PCM_S24LE","sample_rate_hz":48000,"channels":1,"sample_count":48000}, upstream_producer_sha256=raw_producer["record_sha256"], q1_readback_sha256=None))
    metadata = sha256_bytes(b"BAI:TASK089:FIXTURE_MEDIA:V1\0" + canonical_json_bytes(producer["media"]))
    binding = custody_staged_binding_sha256(opaque_artifact_id="fixture.canonical.1", logical_slot_ref="fixture.canonical.slot", generation_revision=1, owner_subject_revision_sha256=subject["record_sha256"], purpose="CAPTURE_CANONICAL_PUBLISH", artifact_class=ArtifactClass.CANONICAL_PCM, content_sha256=producer["content_sha256"], media_metadata_sha256=metadata, opened_physical_identity_sha256=h("physical-canonical"), cipher_backend_identity_sha256=h("cipher-canonical"), consent_rights_revision_sha256=grant["record_sha256"], observed_at=T1, fresh_until=T9)
    event = PrivateMediaGenerationEvent.create(event_kind=GenerationEventKind.GENERATION_PUBLISHED, logical_slot_ref="fixture.canonical.slot", artifact_class=ArtifactClass.CANONICAL_PCM, event_revision=1, predecessor_event_sha256=None, owner_subject_revision_sha256=subject["record_sha256"], purpose="CAPTURE_CANONICAL_PUBLISH", consent_rights_revision_sha256=grant["record_sha256"], created_at=T0, observed_at=T1, fresh_until=T9, trusted_time_binding_sha256=h("canonical-time"), published_generation_revision=1, opaque_artifact_id="fixture.canonical.1", custody_binding_sha256=binding, content_sha256=producer["content_sha256"], media_metadata_sha256=metadata, opened_physical_identity_sha256=h("physical-canonical"), cipher_backend_identity_sha256=h("cipher-canonical"), target_generation_revision=None, target_publish_event_sha256=None, tombstone_decision_sha256=None)
    receipt = PrivateMediaCustodyReceipt.create(opaque_artifact_id="fixture.canonical.1", logical_slot_ref="fixture.canonical.slot", generation_revision=1, predecessor_receipt_sha256=None, custody_binding_sha256=binding, owner_subject_revision_sha256=subject["record_sha256"], purpose="CAPTURE_CANONICAL_PUBLISH", artifact_class=ArtifactClass.CANONICAL_PCM, content_sha256=producer["content_sha256"], media_metadata_sha256=metadata, opened_physical_identity_sha256=h("physical-canonical"), cipher_backend_identity_sha256=h("cipher-canonical"), consent_rights_revision_sha256=grant["record_sha256"], generation_event_sha256=event.event_sha256, event_head_sha256=event.event_sha256, observed_at=T1, fresh_until=T9)
    custody = own("Task089CustodyFixtureV1", common("Task089CustodyFixtureV1", producer_sha256=producer["record_sha256"], custody_receipt=receipt.as_dict(), generation_events=[event.as_dict()]))
    request = common("Task089AdoptionRequestFixtureV1", subject_sha256=subject["record_sha256"], producer_sha256=producer["record_sha256"], custody_sha256=custody["record_sha256"], grant_sha256=grant["record_sha256"], adoption_operation_id="OP-66666666666666666666666666", expected_registry_generation=0, predecessor_registration_sha256=None, semantic_key_sha256=None); request["semantic_key_sha256"] = semantic_key(request); request = own("Task089AdoptionRequestFixtureV1", request)
    snapshot = {"asset_id":"ASSET-77777777777777777777777777","production_job_id":subject["production_job_id"],"asset_type":"AUDIO","asset_role":"CANONICAL_PCM","logical_uri":"asset://JOB-00000000000000000000000000/owner-voice/canonical_pcm/ASSET-77777777777777777777777777","checksum":producer["content_sha256"],"asset_version":1,"producer_operation_id":request["adoption_operation_id"],"custody_receipt_sha256":receipt.receipt_sha256}
    registration = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=request["record_sha256"], outcome="REGISTERED", registry_generation=1, asset_snapshot=snapshot))
    readback = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=request["record_sha256"], registration_sha256=registration["record_sha256"], observation_kind="SNAPSHOT", observed_subject_sha256=subject["record_sha256"], observed_grant_sha256=grant["record_sha256"], observed_registry_generation=1, selected_asset_id=snapshot["asset_id"], selected_registration_sha256=registration["record_sha256"], observed_custody_sha256=custody["record_sha256"], fixture_session="fixture-session", observed_at=T2, fresh_until=T9))
    records = [subject, raw_grant, raw_producer, grant, producer, custody, request, registration, readback]
    bundle = {"record_type":"Task089FixtureBundleV1","schema_version":1,"fixture_case":"fixture-raw","fixture_session":"fixture-session","observed_at":T2,"records":records,"fixture_only":True,"authority_created":False,"execution_authorized":False,"owner_port_contract_status":"NOT_BOUND","bundle_sha256":None}; bundle["bundle_sha256"] = bundle_digest(bundle)
    return bundle, {"S":subject,"G":grant,"P":producer,"CU":custody,"R":request,"A":registration,"O":readback}


def q2_pair_bundle(*, processed_outcome: str = "REGISTERED", processed_observation: str = "SNAPSHOT", copy_outcome: str = "REGISTERED", copy_observation: str = "SNAPSHOT") -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    payload, canonical = canonical_bundle()
    subject = canonical["S"]
    q1 = canonical["O"]["record_sha256"]
    def branch(role: str, grant_revision: int, asset_id: str, operation: str, upstream: dict[str, object] | None, *, outcome: str, observation: str) -> dict[str, dict[str, object]]:
        purpose, grant_operation, output = {
            "PROCESSED_SPEECH_CONTINUOUS": ("QUALITY_SPEECH_CONTINUOUS_PUBLISH", "QUALITY_FINISHING", "TASK048_SPEECH_CONTINUOUS_OUTPUT"),
            "TRAINING_COPY": ("QUALITY_TRAINING_COPY_PUBLISH", "TRAINING_COPY_CREATION", "TASK048_TRAINING_COPY_OUTPUT"),
        }[role]
        artifact = ArtifactClass(role)
        grant = own("Task089PurposeGrantFixtureV1", common("Task089PurposeGrantFixtureV1", subject_sha256=subject["record_sha256"], scope="OWNER_VOICE_DATA_PREPARATION", operation=grant_operation, output_role=role, decision="ALLOW", policy_revision=2, grant_revision=grant_revision, issued_at=T0, expires_at=T9, q1_readback_sha256=q1))
        producer = own("Task089ProducerOutputFixtureV1", common("Task089ProducerOutputFixtureV1", subject_sha256=subject["record_sha256"], grant_sha256=grant["record_sha256"], producer_task="TASK-048", producer_output_role=output, asset_role=role, producer_operation_id=operation, output_sequence=1, content_sha256=h("content-" + role), media={"format":"PCM_S24LE","sample_rate_hz":48000,"channels":1,"sample_count":48000}, upstream_producer_sha256=None if upstream is None else upstream["P"]["record_sha256"], q1_readback_sha256=q1))
        metadata = sha256_bytes(b"BAI:TASK089:FIXTURE_MEDIA:V1\0" + canonical_json_bytes(producer["media"]))
        slot = "fixture." + role.lower() + ".slot"; artifact_id = "fixture." + role.lower() + ".1"
        binding = custody_staged_binding_sha256(opaque_artifact_id=artifact_id, logical_slot_ref=slot, generation_revision=1, owner_subject_revision_sha256=subject["record_sha256"], purpose=purpose, artifact_class=artifact, content_sha256=producer["content_sha256"], media_metadata_sha256=metadata, opened_physical_identity_sha256=h("physical-" + role), cipher_backend_identity_sha256=h("cipher-" + role), consent_rights_revision_sha256=grant["record_sha256"], observed_at=T1, fresh_until=T9)
        event = PrivateMediaGenerationEvent.create(event_kind=GenerationEventKind.GENERATION_PUBLISHED, logical_slot_ref=slot, artifact_class=artifact, event_revision=1, predecessor_event_sha256=None, owner_subject_revision_sha256=subject["record_sha256"], purpose=purpose, consent_rights_revision_sha256=grant["record_sha256"], created_at=T0, observed_at=T1, fresh_until=T9, trusted_time_binding_sha256=h("time-" + role), published_generation_revision=1, opaque_artifact_id=artifact_id, custody_binding_sha256=binding, content_sha256=producer["content_sha256"], media_metadata_sha256=metadata, opened_physical_identity_sha256=h("physical-" + role), cipher_backend_identity_sha256=h("cipher-" + role), target_generation_revision=None, target_publish_event_sha256=None, tombstone_decision_sha256=None)
        receipt = PrivateMediaCustodyReceipt.create(opaque_artifact_id=artifact_id, logical_slot_ref=slot, generation_revision=1, predecessor_receipt_sha256=None, custody_binding_sha256=binding, owner_subject_revision_sha256=subject["record_sha256"], purpose=purpose, artifact_class=artifact, content_sha256=producer["content_sha256"], media_metadata_sha256=metadata, opened_physical_identity_sha256=h("physical-" + role), cipher_backend_identity_sha256=h("cipher-" + role), consent_rights_revision_sha256=grant["record_sha256"], generation_event_sha256=event.event_sha256, event_head_sha256=event.event_sha256, observed_at=T1, fresh_until=T9)
        custody = own("Task089CustodyFixtureV1", common("Task089CustodyFixtureV1", producer_sha256=producer["record_sha256"], custody_receipt=receipt.as_dict(), generation_events=[event.as_dict()]))
        request = common("Task089AdoptionRequestFixtureV1", subject_sha256=subject["record_sha256"], producer_sha256=producer["record_sha256"], custody_sha256=custody["record_sha256"], grant_sha256=grant["record_sha256"], adoption_operation_id=("OP-BBBBBBBBBBBBBBBBBBBBBBBBBB" if role.startswith("PROCESSED") else "OP-CCCCCCCCCCCCCCCCCCCCCCCCCC"), expected_registry_generation=0, predecessor_registration_sha256=None, semantic_key_sha256=None); request["semantic_key_sha256"] = semantic_key(request); request = own("Task089AdoptionRequestFixtureV1", request)
        snapshot = {"asset_id":asset_id,"production_job_id":subject["production_job_id"],"asset_type":"AUDIO","asset_role":role,"logical_uri":f"asset://JOB-00000000000000000000000000/owner-voice/{role.lower()}/{asset_id}","checksum":producer["content_sha256"],"asset_version":1,"producer_operation_id":request["adoption_operation_id"],"custody_receipt_sha256":receipt.receipt_sha256} if outcome == "REGISTERED" else None
        registration = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=request["record_sha256"], outcome=outcome, registry_generation=1 if outcome == "REGISTERED" else 0, asset_snapshot=snapshot))
        if observation == "SNAPSHOT":
            readback_fields = dict(registration_sha256=registration["record_sha256"], observed_subject_sha256=subject["record_sha256"], observed_grant_sha256=grant["record_sha256"], observed_registry_generation=1, selected_asset_id=asset_id, selected_registration_sha256=registration["record_sha256"], observed_custody_sha256=custody["record_sha256"])
        elif observation == "NO_WRITE":
            readback_fields = dict(registration_sha256=registration["record_sha256"], observed_subject_sha256=subject["record_sha256"], observed_grant_sha256=grant["record_sha256"], observed_registry_generation=0, selected_asset_id=None, selected_registration_sha256=None, observed_custody_sha256=custody["record_sha256"])
        elif observation == "UNRESOLVED":
            readback_fields = dict(registration_sha256=registration["record_sha256"], observed_subject_sha256=None, observed_grant_sha256=None, observed_registry_generation=0, selected_asset_id=None, selected_registration_sha256=None, observed_custody_sha256=None)
        else:
            readback_fields = dict(registration_sha256=None, observed_subject_sha256=None, observed_grant_sha256=None, observed_registry_generation=None, selected_asset_id=None, selected_registration_sha256=None, observed_custody_sha256=None)
        readback = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=request["record_sha256"], observation_kind=observation, fixture_session="fixture-session", observed_at=T2, fresh_until=T9, **readback_fields))
        return {"G":grant,"P":producer,"CU":custody,"R":request,"A":registration,"O":readback}
    processed = branch("PROCESSED_SPEECH_CONTINUOUS", 1, "ASSET-88888888888888888888888888", "OP-AAAAAAAAAAAAAAAAAAAAAAAAAA", None, outcome=processed_outcome, observation=processed_observation)
    copy = branch("TRAINING_COPY", 2, "ASSET-99999999999999999999999999", "OP-AAAAAAAAAAAAAAAAAAAAAAAAAA", processed, outcome=copy_outcome, observation=copy_observation)
    payload["records"].extend([processed[k] for k in ("G","P","CU","R","A","O")] + [copy[k] for k in ("G","P","CU","R","A","O")])
    payload["bundle_sha256"] = bundle_digest(payload)
    return payload, {"P":processed,"C":copy}


def test_wire_digest_current_and_no_effect() -> None:
    payload, r = raw_bundle()
    bundle = parse_fixture_bundle(canonical_json_bytes(payload))
    result = assess_adoption_fixture(bundle, request_sha256=r["R"]["record_sha256"], readback_sha256=r["O"]["record_sha256"])
    output = result.to_dict()
    assert output["fixture_state"] == "CONSISTENT_REGISTERED"
    assert output["reason_code"] == "FIXTURE_RELATIONS_MATCH"
    assert output["guard_status"] == "UNAVAILABLE"
    assert output["fixture_only"] is True and output["authority_created"] is False and output["execution_authorized"] is False
    assert output["private_media_effect_count"] == output["asset_adoption_count"] == 0
    assert parse_fixture_bundle(canonical_json_bytes(payload)).to_dict() == payload


def test_pure_api_effect_tripwires_cover_parser_assessment_and_handoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pure APIs must not reach file, DB, network, process, or wall-clock gateways."""
    # Import effectful Product boundaries before installing the pure-API fence.
    # Import/bootstrap reads are outside the fence; calls into these boundaries are not.
    import ai_video_production.ingest as ingest_module
    import ai_video_production.privacy_guard as privacy_guard_module

    raw, records = raw_bundle()
    pair_raw, pair = q2_pair_bundle()
    events: list[str] = []
    def forbidden(name: str):
        def call(*_args: object, **_kwargs: object) -> object:
            events.append(name)
            raise AssertionError(name)
        return call
    real_datetime = task089_module.datetime
    class NoClock:
        strptime = staticmethod(real_datetime.strptime)
        fromisoformat = staticmethod(real_datetime.fromisoformat)
        now = staticmethod(forbidden("clock"))
        utcnow = staticmethod(forbidden("clock"))
    monkeypatch.setattr(builtins, "open", forbidden("file"))
    monkeypatch.setattr(sqlite3, "connect", forbidden("sqlite"))
    monkeypatch.setattr(socket, "socket", forbidden("network"))
    monkeypatch.setattr(subprocess, "Popen", forbidden("process"))
    monkeypatch.setattr(task089_module, "datetime", NoClock)
    monkeypatch.setattr(task082_module, "compile_fixture_write_lease_admission", forbidden("write_lease"))
    monkeypatch.setattr(task082_module, "compile_fixture_read_lease_admission", forbidden("read_lease"))
    monkeypatch.setattr(task082_module, "mint_fixture_lease_sentinel", forbidden("lease_sentinel"))
    monkeypatch.setattr(ingest_module.AssetIngestService, "ingest", forbidden("asset_ingest"))
    monkeypatch.setattr(privacy_guard_module, "classify_publication_gate", forbidden("publication"))
    bundle = parse_fixture_bundle(canonical_json_bytes(raw))
    assessment = assess_adoption_fixture(bundle, request_sha256=records["R"]["record_sha256"], readback_sha256=records["O"]["record_sha256"])
    pair_bundle = parse_fixture_bundle(canonical_json_bytes(pair_raw))
    handoff = build_q2_pair_handoff_fixture(pair_bundle, processed_request_sha256=pair["P"]["R"]["record_sha256"], processed_readback_sha256=pair["P"]["O"]["record_sha256"], copy_request_sha256=pair["C"]["R"]["record_sha256"], copy_readback_sha256=pair["C"]["O"]["record_sha256"])
    malformed = dict(raw, records=[dict(raw["records"][0], unexpected_private_field="never-open") , *raw["records"][1:]])
    malformed["bundle_sha256"] = bundle_digest(malformed)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(malformed))
    assert assessment.fixture_state == "CONSISTENT_REGISTERED"
    assert handoff.terminal_binding_status == "NOT_BOUND"
    assert exc.value.code == "MALFORMED_FIXTURE"
    assert events == []


def test_canonical_pcm_exact_nine_record_closure_is_consistent() -> None:
    payload, r = canonical_bundle()
    assert len(payload["records"]) == 9
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R"]["record_sha256"], readback_sha256=r["O"]["record_sha256"])
    assert result.fixture_state == "CONSISTENT_REGISTERED"


@pytest.mark.parametrize("prior_tombstone", [False, True])
def test_later_generation_exact_prefix_is_current_even_after_historical_tombstone(prior_tombstone: bool) -> None:
    payload, records = later_raw_generation_bundle(prior_tombstone=prior_tombstone)
    assert records["P1"]["output_sequence"] == records["P2"]["output_sequence"] == 1
    assert records["P1"]["producer_operation_id"] != records["P2"]["producer_operation_id"]
    assert records["CU2"]["generation_events"][:len(records["CU1"]["generation_events"])] == records["CU1"]["generation_events"]
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=records["R2"]["record_sha256"], readback_sha256=records["O2"]["record_sha256"])
    assert (result.fixture_state, result.reason_code) == ("CONSISTENT_REGISTERED", "FIXTURE_RELATIONS_MATCH")


def test_later_generation_prefix_and_operation_coordinate_faults_fail_closed() -> None:
    payload, records = later_raw_generation_bundle(prior_tombstone=True)
    shortened = dict(records["CU2"], generation_events=records["CU2"]["generation_events"][1:])
    bad_prefix, _ = rewire_successor_custody(payload, records, shortened)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(bad_prefix))
    assert exc.value.code == "REFERENCE_MISMATCH"
    duplicate_producer = own("Task089ProducerOutputFixtureV1", dict(records["P2"], producer_operation_id=records["P1"]["producer_operation_id"], output_sequence=records["P1"]["output_sequence"]))
    duplicate_custody = dict(records["CU2"], producer_sha256=duplicate_producer["record_sha256"])
    duplicate_bundle, _ = rewire_successor_custody(payload, records, duplicate_custody)
    duplicate_bundle["records"] = [duplicate_producer if item["record_sha256"] == records["P2"]["record_sha256"] else item for item in duplicate_bundle["records"]]
    duplicate_bundle["bundle_sha256"] = bundle_digest(duplicate_bundle)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(duplicate_bundle))
    assert exc.value.code == "REFERENCE_MISMATCH"


def test_later_generation_wrong_predecessor_subject_grant_slot_and_staged_alias_fail_closed() -> None:
    payload, records = later_raw_generation_bundle()
    wrong_predecessor = dict(records["R2"], predecessor_registration_sha256=records["A2"]["record_sha256"], semantic_key_sha256=None)
    wrong_predecessor["semantic_key_sha256"] = semantic_key(wrong_predecessor)
    wrong_predecessor = own("Task089AdoptionRequestFixtureV1", wrong_predecessor)
    predecessor_bundle = dict(payload, records=[wrong_predecessor if item["record_sha256"] == records["R2"]["record_sha256"] else item for item in payload["records"]])
    predecessor_bundle["bundle_sha256"] = bundle_digest(predecessor_bundle)
    with pytest.raises(Task089ContractError):
        parse_fixture_bundle(canonical_json_bytes(predecessor_bundle))
    wrong_subject = own("Task089ProducerOutputFixtureV1", dict(records["P2"], subject_sha256=h("wrong-subject")))
    subject_bundle = dict(payload, records=[wrong_subject if item["record_sha256"] == records["P2"]["record_sha256"] else item for item in payload["records"]])
    subject_bundle["bundle_sha256"] = bundle_digest(subject_bundle)
    with pytest.raises(Task089ContractError):
        parse_fixture_bundle(canonical_json_bytes(subject_bundle))
    wrong_grant = own("Task089ProducerOutputFixtureV1", dict(records["P2"], grant_sha256=h("wrong-grant")))
    grant_bundle = dict(payload, records=[wrong_grant if item["record_sha256"] == records["P2"]["record_sha256"] else item for item in payload["records"]])
    grant_bundle["bundle_sha256"] = bundle_digest(grant_bundle)
    with pytest.raises(Task089ContractError):
        parse_fixture_bundle(canonical_json_bytes(grant_bundle))
    changed_slot = dict(records["CU2"], custody_receipt=dict(records["CU2"]["custody_receipt"], logical_slot_ref="fixture.raw.other"))
    slot_bundle, _ = rewire_successor_custody(payload, records, changed_slot)
    with pytest.raises(Task089ContractError):
        parse_fixture_bundle(canonical_json_bytes(slot_bundle))
    staged_alias = dict(records["CU2"], custody_receipt=dict(records["CU2"]["custody_receipt"], custody_binding_sha256=records["CU2"]["custody_receipt"]["receipt_sha256"]))
    alias_bundle, _ = rewire_successor_custody(payload, records, staged_alias)
    with pytest.raises(Task089ContractError):
        parse_fixture_bundle(canonical_json_bytes(alias_bundle))


def test_extra_later_publish_is_not_a_valid_successor_suffix() -> None:
    payload, records = later_raw_generation_bundle()
    published = PrivateMediaGenerationEvent.from_mapping(records["CU2"]["generation_events"][-1])
    content = h("extra-publish-content")
    metadata = h("extra-publish-media")
    physical = h("extra-publish-physical")
    cipher = h("extra-publish-cipher")
    binding = custody_staged_binding_sha256(opaque_artifact_id="fixture.raw.3", logical_slot_ref=published.logical_slot_ref, generation_revision=3, owner_subject_revision_sha256=published.owner_subject_revision_sha256, purpose=published.purpose, artifact_class=published.artifact_class, content_sha256=content, media_metadata_sha256=metadata, opened_physical_identity_sha256=physical, cipher_backend_identity_sha256=cipher, consent_rights_revision_sha256=published.consent_rights_revision_sha256, observed_at=T2, fresh_until=T9)
    later = PrivateMediaGenerationEvent.create(
        event_kind=GenerationEventKind.GENERATION_PUBLISHED,
        logical_slot_ref=published.logical_slot_ref,
        artifact_class=published.artifact_class,
        event_revision=published.event_revision + 1,
        predecessor_event_sha256=published.event_sha256,
        owner_subject_revision_sha256=published.owner_subject_revision_sha256,
        purpose=published.purpose,
        consent_rights_revision_sha256=published.consent_rights_revision_sha256,
        created_at=T2,
        observed_at=T2,
        fresh_until=T9,
        trusted_time_binding_sha256=h("extra-publish-time"),
        published_generation_revision=3,
        opaque_artifact_id="fixture.raw.3",
        custody_binding_sha256=binding,
        content_sha256=content,
        media_metadata_sha256=metadata,
        opened_physical_identity_sha256=physical,
        cipher_backend_identity_sha256=cipher,
        target_generation_revision=None,
        target_publish_event_sha256=None,
        tombstone_decision_sha256=None,
    )
    extra = dict(records["CU2"], generation_events=[*records["CU2"]["generation_events"], later.as_dict()])
    extra_bundle, _ = rewire_successor_custody(payload, records, extra)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(extra_bundle))
    assert exc.value.code == "REFERENCE_MISMATCH"


def test_q2_pair_exact_twenty_one_record_closure_builds_nonlive_handoff() -> None:
    payload, q2 = q2_pair_bundle()
    assert len(payload["records"]) == 21
    assert q2["P"]["P"]["producer_operation_id"] == q2["C"]["P"]["producer_operation_id"]
    assert q2["P"]["P"]["output_sequence"] == q2["C"]["P"]["output_sequence"] == 1
    bundle = parse_fixture_bundle(canonical_json_bytes(payload))
    handoff = build_q2_pair_handoff_fixture(bundle, processed_request_sha256=q2["P"]["R"]["record_sha256"], processed_readback_sha256=q2["P"]["O"]["record_sha256"], copy_request_sha256=q2["C"]["R"]["record_sha256"], copy_readback_sha256=q2["C"]["O"]["record_sha256"])
    assert handoff.consumer_owner_task == "TASK-090"
    assert handoff.terminal_binding_status == handoff.owner_port_contract_status == "NOT_BOUND"
    assert handoff.fixture_only is True and handoff.authority_created is False and handoff.execution_authorized is False


def test_processed_and_copy_minimal_closures_have_exact_fifteen_and_seventeen_records() -> None:
    payload, q2 = q2_pair_bundle()
    processed = dict(payload); processed["records"] = payload["records"][:9] + [q2["P"][key] for key in ("G", "P", "CU", "R", "A", "O")]; processed["bundle_sha256"] = bundle_digest(processed)
    assert len(processed["records"]) == 15
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(processed)), request_sha256=q2["P"]["R"]["record_sha256"], readback_sha256=q2["P"]["O"]["record_sha256"])
    assert result.fixture_state == "CONSISTENT_REGISTERED"
    copy = dict(payload); copy["records"] = payload["records"][:9] + [q2["P"][key] for key in ("G", "P")] + [q2["C"][key] for key in ("G", "P", "CU", "R", "A", "O")]; copy["bundle_sha256"] = bundle_digest(copy)
    assert len(copy["records"]) == 17
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(copy)), request_sha256=q2["C"]["R"]["record_sha256"], readback_sha256=q2["C"]["O"]["record_sha256"])
    assert result.fixture_state == "CONSISTENT_REGISTERED"


def test_schema_document_root_accepts_generated_e_and_h_outputs() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = globals()["validator"](schema)
    raw, records = raw_bundle()
    assessment = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(raw)), request_sha256=records["R"]["record_sha256"], readback_sha256=records["O"]["record_sha256"])
    assert list(validator.iter_errors(assessment.to_dict())) == []
    q2, branches = q2_pair_bundle()
    handoff = build_q2_pair_handoff_fixture(parse_fixture_bundle(canonical_json_bytes(q2)), processed_request_sha256=branches["P"]["R"]["record_sha256"], processed_readback_sha256=branches["P"]["O"]["record_sha256"], copy_request_sha256=branches["C"]["R"]["record_sha256"], copy_readback_sha256=branches["C"]["O"]["record_sha256"])
    assert list(validator.iter_errors(handoff.to_dict())) == []
    invalid_state_reason = assessment.to_dict()
    invalid_state_reason["fixture_state"] = "CONFLICT"
    assert list(validator.iter_errors(invalid_state_reason))
    invalid_contract_order = assessment.to_dict()
    invalid_contract_order["required_owner_contracts"] = list(reversed(invalid_contract_order["required_owner_contracts"]))
    assert list(validator.iter_errors(invalid_contract_order))
    invalid_pair = handoff.to_dict()
    invalid_pair["terminal_binding_status"] = "BOUND"
    assert list(validator.iter_errors(invalid_pair))


def test_public_parser_rejects_every_standalone_input_or_output_record_and_nested_bundle() -> None:
    payload, records = raw_bundle()
    assessment = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=records["R"]["record_sha256"], readback_sha256=records["O"]["record_sha256"])
    pair_payload, branches = q2_pair_bundle()
    handoff = build_q2_pair_handoff_fixture(parse_fixture_bundle(canonical_json_bytes(pair_payload)), processed_request_sha256=branches["P"]["R"]["record_sha256"], processed_readback_sha256=branches["P"]["O"]["record_sha256"], copy_request_sha256=branches["C"]["R"]["record_sha256"], copy_readback_sha256=branches["C"]["O"]["record_sha256"])
    for standalone in [*payload["records"], assessment.to_dict(), handoff.to_dict()]:
        with pytest.raises(Task089ContractError) as exc:
            parse_fixture_bundle(canonical_json_bytes(standalone))
        assert exc.value.code == "MALFORMED_FIXTURE"
    nested = dict(payload, records=[*payload["records"], payload])
    nested["bundle_sha256"] = bundle_digest(nested)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(nested))
    assert exc.value.code == "MALFORMED_FIXTURE"


def test_schema_root_closes_each_input_role_and_all_registration_observation_arms() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    check = validator(schema)
    _, r = raw_bundle()
    for record in (r["S"], r["G"], r["P"], r["CU"], r["R"], r["A"], r["O"]):
        assert list(check.iter_errors(record)) == []
    for role, task, output, scope, operation in (
        ("RAW_CAPTURE", "TASK-047", "TASK047_RAW_CAPTURE_OUTPUT", "OWNER_VOICE_CAPTURE", "CAPTURE_RAW_PUBLISH"),
        ("CANONICAL_PCM", "TASK-047", "TASK047_CANONICAL_PCM_OUTPUT", "OWNER_VOICE_CAPTURE", "CAPTURE_CANONICAL_PUBLISH"),
        ("PROCESSED_SPEECH_CONTINUOUS", "TASK-048", "TASK048_SPEECH_CONTINUOUS_OUTPUT", "OWNER_VOICE_DATA_PREPARATION", "QUALITY_FINISHING"),
        ("TRAINING_COPY", "TASK-048", "TASK048_TRAINING_COPY_OUTPUT", "OWNER_VOICE_DATA_PREPARATION", "TRAINING_COPY_CREATION"),
    ):
        grant = dict(r["G"], output_role=role, scope=scope, operation=operation)
        producer = dict(r["P"], asset_role=role, producer_task=task, producer_output_role=output)
        if role == "CANONICAL_PCM":
            producer["media"] = dict(producer["media"], format="PCM_S24LE")
            producer["upstream_producer_sha256"] = h("schema-canonical-upstream")
        elif role == "PROCESSED_SPEECH_CONTINUOUS":
            grant["q1_readback_sha256"] = h("schema-q1")
            producer["media"] = dict(producer["media"], format="PCM_S24LE")
            producer["q1_readback_sha256"] = h("schema-q1")
        elif role == "TRAINING_COPY":
            grant["q1_readback_sha256"] = h("schema-q1")
            producer["media"] = dict(producer["media"], format="PCM_S24LE")
            producer["upstream_producer_sha256"] = h("schema-processed-upstream")
            producer["q1_readback_sha256"] = h("schema-q1")
        assert list(check.iter_errors(grant)) == []
        assert list(check.iter_errors(producer)) == []
    for outcome in ("REJECTED_NO_WRITE", "COMPLETION_UNKNOWN"):
        registration = dict(r["A"], outcome=outcome, asset_snapshot=None)
        assert list(check.iter_errors(registration)) == []
    for arm in ("SNAPSHOT", "NO_WRITE", "UNRESOLVED", "UNAVAILABLE", "RESTARTED"):
        readback = dict(r["O"], observation_kind=arm)
        if arm in {"UNAVAILABLE", "RESTARTED"}:
            for key in ("registration_sha256", "observed_subject_sha256", "observed_grant_sha256", "observed_registry_generation", "selected_asset_id", "selected_registration_sha256", "observed_custody_sha256"):
                readback[key] = None
        elif arm == "UNRESOLVED":
            for key in ("observed_subject_sha256", "observed_grant_sha256", "selected_asset_id", "selected_registration_sha256", "observed_custody_sha256"):
                readback[key] = None
        elif arm == "NO_WRITE":
            readback["selected_asset_id"] = None
            readback["selected_registration_sha256"] = None
        assert list(check.iter_errors(readback)) == []
    bad_grant = dict(r["G"], q1_readback_sha256=h("capture-must-not-q1"))
    bad_canonical = dict(r["P"], asset_role="CANONICAL_PCM", producer_output_role="TASK047_CANONICAL_PCM_OUTPUT", media={"format":"PCM_S24LE","sample_rate_hz":48000,"channels":1,"sample_count":48000})
    bad_processed = dict(r["P"], asset_role="PROCESSED_SPEECH_CONTINUOUS", producer_task="TASK-048", producer_output_role="TASK048_SPEECH_CONTINUOUS_OUTPUT", media={"format":"PCM_S24LE","sample_rate_hz":48000,"channels":1,"sample_count":48000})
    assert list(check.iter_errors(bad_grant))
    assert list(check.iter_errors(bad_canonical))
    assert list(check.iter_errors(bad_processed))


def test_current_no_write_and_unavailable_are_explicit_not_success() -> None:
    payload, r = raw_bundle(outcome="REJECTED_NO_WRITE", observation="NO_WRITE")
    no_write = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R"]["record_sha256"], readback_sha256=r["O"]["record_sha256"])
    assert (no_write.fixture_state, no_write.reason_code) == ("NOT_READY", "REGISTRATION_REJECTED")
    payload, r = raw_bundle(outcome="REGISTERED", observation="UNAVAILABLE")
    unknown = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R"]["record_sha256"], readback_sha256=r["O"]["record_sha256"])
    assert (unknown.fixture_state, unknown.reason_code) == ("UNKNOWN", "OUTCOME_UNKNOWN")
    payload, r = raw_bundle(observation="UNRESOLVED")
    unknown = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R"]["record_sha256"], readback_sha256=r["O"]["record_sha256"])
    assert (unknown.fixture_state, unknown.reason_code) == ("UNKNOWN", "OUTCOME_UNKNOWN")
    registration = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=r["R"]["record_sha256"], outcome="COMPLETION_UNKNOWN", registry_generation=1, asset_snapshot=None))
    readback = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=r["R"]["record_sha256"], registration_sha256=registration["record_sha256"], observation_kind="UNRESOLVED", observed_subject_sha256=None, observed_grant_sha256=None, observed_registry_generation=1, selected_asset_id=None, selected_registration_sha256=None, observed_custody_sha256=None, fixture_session="fixture-session", observed_at=T2, fresh_until=T9))
    payload["records"][-2:] = [registration, readback]
    payload["bundle_sha256"] = bundle_digest(payload)
    unknown_next = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R"]["record_sha256"], readback_sha256=readback["record_sha256"])
    assert (unknown_next.fixture_state, unknown_next.reason_code) == ("UNKNOWN", "OUTCOME_UNKNOWN")
    for decision in ("DENY", "UNKNOWN"):
        denied, denied_records = raw_bundle(grant_decision=decision)
        result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(denied)), request_sha256=denied_records["R"]["record_sha256"], readback_sha256=denied_records["O"]["record_sha256"])
        assert (result.fixture_state, result.reason_code) == ("NOT_READY", "PURPOSE_NOT_ALLOWED")
    payload, r = raw_bundle(observation="RESTARTED")
    restarted = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R"]["record_sha256"], readback_sha256=r["O"]["record_sha256"])
    assert (restarted.fixture_state, restarted.reason_code) == ("UNKNOWN", "SESSION_NOT_CURRENT")



@pytest.mark.parametrize(
    "observation,wrong_outcome",
    [
        ("NO_WRITE", "COMPLETION_UNKNOWN"),
        ("UNRESOLVED", "REJECTED_NO_WRITE"),
    ],
)
def test_non_success_readback_arm_requires_its_exact_causal_registration_outcome(observation: str, wrong_outcome: str) -> None:
    payload, records = raw_bundle(outcome="REJECTED_NO_WRITE", observation="NO_WRITE")
    wrong_registration = own(
        "Task089RegistrationFixtureV1",
        common(
            "Task089RegistrationFixtureV1",
            request_sha256=records["R"]["record_sha256"],
            outcome=wrong_outcome,
            registry_generation=records["R"]["expected_registry_generation"],
            asset_snapshot=None,
        ),
    )
    if observation == "NO_WRITE":
        readback_fields = dict(
            registration_sha256=wrong_registration["record_sha256"],
            observed_subject_sha256=records["S"]["record_sha256"],
            observed_grant_sha256=records["G"]["record_sha256"],
            observed_registry_generation=wrong_registration["registry_generation"],
            selected_asset_id=None,
            selected_registration_sha256=None,
            observed_custody_sha256=records["CU"]["record_sha256"],
        )
    else:
        readback_fields = dict(
            registration_sha256=wrong_registration["record_sha256"],
            observed_subject_sha256=None,
            observed_grant_sha256=None,
            observed_registry_generation=wrong_registration["registry_generation"],
            selected_asset_id=None,
            selected_registration_sha256=None,
            observed_custody_sha256=None,
        )
    readback = own(
        "Task089CurrentReadbackFixtureV1",
        common(
            "Task089CurrentReadbackFixtureV1",
            request_sha256=records["R"]["record_sha256"],
            observation_kind=observation,
            fixture_session="fixture-session",
            observed_at=T2,
            fresh_until=T9,
            **readback_fields,
        ),
    )
    payload["records"][-2:] = [wrong_registration, readback]
    payload["bundle_sha256"] = bundle_digest(payload)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code == "REFERENCE_MISMATCH"


@pytest.mark.parametrize("observation", ["NO_WRITE", "UNRESOLVED"])
def test_non_success_readback_arm_requires_observed_generation_to_equal_its_registration(observation: str) -> None:
    outcome = "REJECTED_NO_WRITE" if observation == "NO_WRITE" else "COMPLETION_UNKNOWN"
    payload, records = raw_bundle(outcome=outcome, observation=observation)
    readback = dict(records["O"])
    readback["observed_registry_generation"] = records["A"]["registry_generation"] + 1
    readback["record_sha256"] = None
    readback = own("Task089CurrentReadbackFixtureV1", readback)
    payload["records"][-1] = readback
    payload["bundle_sha256"] = bundle_digest(payload)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code == "REFERENCE_MISMATCH"


@pytest.mark.parametrize("observation", ["UNAVAILABLE", "RESTARTED"])
def test_null_readback_arms_cannot_assert_a_registration(observation: str) -> None:
    payload, records = raw_bundle(observation=observation)
    readback = dict(records["O"])
    readback["registration_sha256"] = records["A"]["record_sha256"]
    readback["record_sha256"] = None
    readback = own("Task089CurrentReadbackFixtureV1", readback)
    payload["records"][-1] = readback
    payload["bundle_sha256"] = bundle_digest(payload)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code == "MALFORMED_FIXTURE"

def test_current_readback_and_grant_expiry_boundaries_are_stale_not_shape_errors() -> None:
    payload, records = raw_bundle()
    expired_readback = own("Task089CurrentReadbackFixtureV1", dict(records["O"], observed_at=T1, fresh_until=T2))
    payload["records"][-1] = expired_readback
    payload["bundle_sha256"] = bundle_digest(payload)
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=records["R"]["record_sha256"], readback_sha256=expired_readback["record_sha256"])
    assert (result.fixture_state, result.reason_code) == ("STALE", "CURRENTNESS_MISMATCH")
    expired_grant, grant_records = raw_bundle(grant_expires_at=T2)
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(expired_grant)), request_sha256=grant_records["R"]["record_sha256"], readback_sha256=grant_records["O"]["record_sha256"])
    assert (result.fixture_state, result.reason_code) == ("STALE", "CURRENTNESS_MISMATCH")


@pytest.mark.parametrize("owner_timestamp", [
    "2026-09-14T00:01:00Z",
    "2026-09-14T00:01:00.1Z",
    "2026-09-14T00:01:00.12Z",
    "2026-09-14T00:01:00.123Z",
    "2026-09-14T00:01:00.1234Z",
    "2026-09-14T00:01:00.12345Z",
    "2026-09-14T00:01:00.123456Z",
    "1999-12-31T23:59:59Z",
])
def test_imported_task082_owner_time_grammar_is_not_narrowed(owner_timestamp: str) -> None:
    payload, records = raw_bundle()
    rebuilt, updated = reseal_raw_publication(
        payload,
        records,
        event_updates={"created_at": owner_timestamp, "observed_at": owner_timestamp},
    )
    result = assess_adoption_fixture(
        parse_fixture_bundle(canonical_json_bytes(rebuilt)),
        request_sha256=updated["R"]["record_sha256"],
        readback_sha256=updated["O"]["record_sha256"],
    )
    assert (result.fixture_state, result.reason_code) == (
        "CONSISTENT_REGISTERED",
        "FIXTURE_RELATIONS_MATCH",
    )


@pytest.mark.parametrize("task089_timestamp", [
    "2026-09-14T00:02:00Z",
    "2026-09-14T00:02:00.1Z",
    "1999-12-31T23:59:59.000000Z",
])
def test_task089_owned_time_grammar_remains_exact_six_fraction_digits_and_year_2000_plus(task089_timestamp: str) -> None:
    payload, _ = raw_bundle()
    payload["observed_at"] = task089_timestamp
    payload["bundle_sha256"] = bundle_digest(payload)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code == "MALFORMED_FIXTURE"


def test_later_valid_tombstone_uses_final_owner_chain_head_and_stales_assessment() -> None:
    payload, records = raw_bundle()
    source = records["CU"]["generation_events"][0]
    published = PrivateMediaGenerationEvent.from_mapping(source)
    tombstone = PrivateMediaGenerationEvent.create(
        event_kind=GenerationEventKind.GENERATION_REVOKED,
        logical_slot_ref=published.logical_slot_ref,
        artifact_class=published.artifact_class,
        event_revision=2,
        predecessor_event_sha256=published.event_sha256,
        owner_subject_revision_sha256=published.owner_subject_revision_sha256,
        purpose=published.purpose,
        consent_rights_revision_sha256=published.consent_rights_revision_sha256,
        created_at=T1,
        observed_at=T2,
        fresh_until=T9,
        trusted_time_binding_sha256=h("tombstone-time"),
        published_generation_revision=None,
        opaque_artifact_id=None,
        custody_binding_sha256=None,
        content_sha256=None,
        media_metadata_sha256=None,
        opened_physical_identity_sha256=None,
        cipher_backend_identity_sha256=None,
        target_generation_revision=published.published_generation_revision,
        target_publish_event_sha256=published.event_sha256,
        tombstone_decision_sha256=h("tombstone-decision"),
    )
    current = derive_generation_currentness(
        [published, tombstone],
        observed_at=T2,
        expected_event_head_sha256=tombstone.event_sha256,
        expected_event_count=2,
        expected_current_custody_binding_sha256=records["CU"]["custody_receipt"]["custody_binding_sha256"],
    )
    assert (current.state, current.reason_code) == (
        CurrentnessState.CURRENTNESS_NOT_CONFIRMED,
        Task082Reason.EVENT_LINEAGE_MISMATCH,
    )
    custody = common("Task089CustodyFixtureV1", producer_sha256=records["P"]["record_sha256"], custody_receipt=records["CU"]["custody_receipt"], generation_events=[source, tombstone.as_dict()])
    custody = own("Task089CustodyFixtureV1", custody)
    request = common("Task089AdoptionRequestFixtureV1", subject_sha256=records["S"]["record_sha256"], producer_sha256=records["P"]["record_sha256"], custody_sha256=custody["record_sha256"], grant_sha256=records["G"]["record_sha256"], adoption_operation_id=records["R"]["adoption_operation_id"], expected_registry_generation=0, predecessor_registration_sha256=None, semantic_key_sha256=None)
    request["semantic_key_sha256"] = semantic_key(request)
    request = own("Task089AdoptionRequestFixtureV1", request)
    registration = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=request["record_sha256"], outcome="REGISTERED", registry_generation=1, asset_snapshot=records["A"]["asset_snapshot"]))
    readback = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=request["record_sha256"], registration_sha256=registration["record_sha256"], observation_kind="SNAPSHOT", observed_subject_sha256=records["S"]["record_sha256"], observed_grant_sha256=records["G"]["record_sha256"], observed_registry_generation=1, selected_asset_id=records["A"]["asset_snapshot"]["asset_id"], selected_registration_sha256=registration["record_sha256"], observed_custody_sha256=custody["record_sha256"], fixture_session="fixture-session", observed_at=T2, fresh_until=T9))
    payload["records"] = [records["S"], records["G"], records["P"], custody, request, registration, readback]
    payload["bundle_sha256"] = bundle_digest(payload)
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=request["record_sha256"], readback_sha256=readback["record_sha256"])
    assert (result.fixture_state, result.reason_code) == ("STALE", "CURRENTNESS_MISMATCH")


@pytest.mark.parametrize("payload", [b'{"record_type":"Task089FixtureBundleV1","record_type":"x"}', b"\xef\xbb\xbf{}", b"[]", b'{"x":NaN}'])
def test_strict_decoder_rejects_ambiguous_or_non_bundle_payloads(payload: bytes) -> None:
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(payload)
    assert exc.value.code == "MALFORMED_FIXTURE"


def test_tamper_and_unknown_fields_fail_without_echo() -> None:
    payload, _ = raw_bundle()
    payload["records"][0]["project_revision"] = 2
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code == "MALFORMED_FIXTURE"
    payload, _ = raw_bundle()
    payload["records"][0]["unknown"] = "private-body-value"
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert str(exc.value) == "MALFORMED_FIXTURE"


def test_hostile_parse_failure_has_fixed_code_without_chained_payload_echo() -> None:
    marker = "private-body-value-should-not-escape"
    payload, _ = raw_bundle()
    payload["records"][0]["unknown"] = marker
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    rendered = "".join(traceback.format_exception(exc.type, exc.value, exc.tb))
    assert str(exc.value) == "MALFORMED_FIXTURE"
    assert marker not in rendered


def test_invalid_date_failure_suppresses_parser_context() -> None:
    payload, records = raw_bundle()
    grant = own("Task089PurposeGrantFixtureV1", dict(records["G"], issued_at="2026-99-99T99:99:99.000000Z"))
    payload["records"][1] = grant
    payload["bundle_sha256"] = bundle_digest(payload)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    rendered = "".join(traceback.format_exception(exc.type, exc.value, exc.tb))
    assert str(exc.value) == "MALFORMED_FIXTURE"
    assert "ValueError" not in rendered


def test_outputs_are_detached_nominal_and_unpickleable() -> None:
    payload, r = raw_bundle()
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R"]["record_sha256"], readback_sha256=r["O"]["record_sha256"])
    a = result.to_dict(); a["fixture_state"] = "CONFLICT"
    assert result.fixture_state == "CONSISTENT_REGISTERED"
    contracts = result.required_owner_contracts
    contracts.append("FORGED")
    assert result.required_owner_contracts == ["CANONICAL_ASSET", "PRIVATE_CUSTODY", "PURPOSE_CONSENT", "OWNER_SUBJECT"]
    with pytest.raises(Task089ContractError) as exc:
        result._body = {}  # type: ignore[attr-defined]
    assert exc.value.code == "MALFORMED_FIXTURE"
    with pytest.raises(TypeError):
        pickle.dumps(result)
    with pytest.raises(TypeError):
        class Forged(type(result)):
            pass
    forged = object.__new__(type(result))
    with pytest.raises(Task089ContractError) as exc:
        forged.to_dict()
    assert exc.value.code == "MALFORMED_FIXTURE"
    with pytest.raises(Task089ContractError):
        Task089AdoptionAssessment()
    with pytest.raises(Task089ContractError):
        Task089Q2PairHandoff()
    with pytest.raises(Task089ContractError):
        Task089FixtureBundle()


def test_bundle_field_views_are_detached_and_have_no_mutable_internal_records() -> None:
    payload, _ = raw_bundle()
    bundle = parse_fixture_bundle(canonical_json_bytes(payload))
    fields = bundle.records
    assert bundle.fixture_case == "fixture-raw" and isinstance(fields, tuple)
    fields[0]["project_id"] = "forged-project"
    assert bundle.to_dict() == payload


def test_all_nominal_readers_and_copy_paths_preserve_detached_issued_bodies() -> None:
    raw, records = raw_bundle()
    assessment = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(raw)), request_sha256=records["R"]["record_sha256"], readback_sha256=records["O"]["record_sha256"])
    pair_raw, pair = q2_pair_bundle()
    pair_bundle = parse_fixture_bundle(canonical_json_bytes(pair_raw))
    handoff = build_q2_pair_handoff_fixture(pair_bundle, processed_request_sha256=pair["P"]["R"]["record_sha256"], processed_readback_sha256=pair["P"]["O"]["record_sha256"], copy_request_sha256=pair["C"]["R"]["record_sha256"], copy_readback_sha256=pair["C"]["O"]["record_sha256"])
    for nominal in (assessment, pair_bundle, handoff):
        body = nominal.to_dict()
        assert all(getattr(nominal, name) == (tuple(value) if name == "records" else value) for name, value in body.items())
        for copier in (copy.copy, copy.deepcopy):
            try:
                clone = copier(nominal)
            except (Task089ContractError, TypeError):
                continue
            assert clone.to_dict() == body
            assert clone.to_dict() is not body
        for forged in (b"\xff", b"[]", b"{}", b'{"x":"' + b"a" * 1_048_577 + b'"}'):
            with pytest.raises((Task089ContractError, AttributeError)):
                object.__setattr__(nominal, "_body", forged)
            assert nominal.to_dict() == body


def test_schema_mirror_is_exact_and_root_mentions_all_contract_variants() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["$id"] == "bai.task089.owner-voice-asset-adoption-currentness.nonlive.v1"
    assert {"subject","grant","producer","custody","request","registration","readback","assessment","pair","bundle"} <= set(schema["$defs"])
    assert len(schema["$defs"]["input"]["oneOf"]) == 7
    payload, _ = raw_bundle()
    assert list(validator(schema).iter_errors(payload)) == []


def test_r2_pinned_schema_resource_is_byte_exact_and_has_all_four_fixture_identifier_arms() -> None:
    """The parser uses only the reviewed in-module TASK-089 schema resource."""
    expected_pattern = "^fixture-[a-z0-9_-]{0,56}$"
    raw = gzip.decompress(base64.b64decode(task089_module._TASK089_SCHEMA_GZIP_B64, validate=True))
    assert hashlib.sha256(raw).hexdigest() == "29d8ff8c4c73abff29d6a6e2d758cb1a3510ac25620aea9f1dc2b5e05178354e"
    assert raw == SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(raw)
    assert [
        schema["$defs"]["subject"]["properties"]["fixture_case"]["pattern"],
        schema["$defs"]["readback"]["properties"]["fixture_session"]["pattern"],
        schema["$defs"]["bundle"]["properties"]["fixture_case"]["pattern"],
        schema["$defs"]["bundle"]["properties"]["fixture_session"]["pattern"],
    ] == [expected_pattern] * 4


@pytest.mark.parametrize("fixture_identifier", ["fixture-", "fixture-1", "fixture-_", "fixture--", "fixture-" + "9" * 56])
def test_r2_fixture_identifier_arms_are_parser_and_assessment_positive(fixture_identifier: str) -> None:
    """All four schema arms and the strict parser accept the R2 identifier domain."""
    payload, records = raw_bundle(fixture_case=fixture_identifier, fixture_session=fixture_identifier)
    bundle = parse_fixture_bundle(canonical_json_bytes(payload))
    assessment = assess_adoption_fixture(bundle, request_sha256=records["R"]["record_sha256"], readback_sha256=records["O"]["record_sha256"])
    assert assessment.fixture_state == "CONSISTENT_REGISTERED"


@pytest.mark.parametrize("fixture_identifier", ["fixture-" + "a" * 57, "case-without-fixture-prefix", "fixture-a!", "fixture-a space"])
def test_r2_fixture_identifier_arms_reject_overlength_missing_prefix_and_forbidden_characters(fixture_identifier: str) -> None:
    payload, _ = raw_bundle(fixture_case=fixture_identifier, fixture_session=fixture_identifier)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert list(validator(schema).iter_errors(payload))
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code == "MALFORMED_FIXTURE"


def test_strict_payload_limit_adjacent_builtin_trees_fail_closed_before_schema_admission() -> None:
    """Exercise generic decoder ceilings without constructing a semantic fixture."""
    def payload(value: object) -> bytes:
        return json.dumps(value, separators=(",", ":")).encode("utf-8")

    shallow: object = {"leaf": "x"}
    for number in range(18):
        shallow = {f"n{number}": shallow}
    assert task089_module._strict_payload(payload(shallow)) == shallow
    too_deep: object = shallow
    too_deep = {"overflow": too_deep}
    with pytest.raises(Task089ContractError) as exc:
        task089_module._strict_payload(payload(too_deep))
    assert exc.value.code == "MALFORMED_FIXTURE"
    assert task089_module._strict_payload(payload({f"f{number}": number for number in range(128)}))
    assert task089_module._strict_payload(payload({"x": list(range(256))}))
    assert task089_module._strict_payload(payload({"text": "x" * 4096}))
    assert task089_module._strict_payload(payload({"text": "é" * 2048}))
    byte_edge = b"{}" + b" " * (1_048_576 - 2)
    assert task089_module._strict_payload(byte_edge) == {}
    with pytest.raises(Task089ContractError) as exc:
        task089_module._strict_payload(byte_edge + b" ")
    assert exc.value.code == "MALFORMED_FIXTURE"
    # Exact node seam: 1 dict + 1 outer list + 128 inner lists + 32638 leaves.
    node_32768 = {"x": [[None] * 253] + [[None] * 255 for _ in range(127)]}
    node_32769 = {"x": [[None] * 254] + [[None] * 255 for _ in range(127)]}
    assert task089_module._strict_payload(payload(node_32768)) == node_32768
    for oversized in ({f"f{number}": number for number in range(129)}, {"x": list(range(257))}, {"text": "x" * 4097}, {"text": "é" * 2049}, node_32769):
        with pytest.raises(Task089ContractError) as exc:
            task089_module._strict_payload(payload(oversized))
        assert exc.value.code == "MALFORMED_FIXTURE"
    with pytest.raises(Task089ContractError) as exc:
        task089_module._strict_payload(b'{"x":"' + b"a" * 1_048_577 + b'"}')
    assert exc.value.code == "MALFORMED_FIXTURE"


def test_r2_completion_matrix_has_named_self_contained_coverage() -> None:
    """Keep the accepted non-live test-matrix routing reviewable in this file."""
    coverage = {
        "WIRE": ("test_strict_decoder_rejects_ambiguous_or_non_bundle_payloads", "test_public_parser_rejects_every_standalone_input_or_output_record_and_nested_bundle", "test_r2_fixture_identifier_arms_are_parser_and_assessment_positive", "test_r2_fixture_identifier_arms_reject_overlength_missing_prefix_and_forbidden_characters", "test_strict_payload_limit_adjacent_builtin_trees_fail_closed_before_schema_admission"),
        "DIGEST": ("test_tamper_and_unknown_fields_fail_without_echo", "test_role_digest_integer_and_currentness_faults_fail_closed"),
        "ROLE": ("test_schema_root_closes_each_input_role_and_all_registration_observation_arms", "test_role_digest_integer_and_currentness_faults_fail_closed"),
        "IDENTITY": ("test_historical_different_request_semantic_and_same_output_contenders_conflict", "test_selected_same_request_registration_is_structural_then_conflict"),
        "CUSTODY": ("test_later_generation_exact_prefix_is_current_even_after_historical_tombstone", "test_later_generation_wrong_predecessor_subject_grant_slot_and_staged_alias_fail_closed"),
        "CURRENT": ("test_current_no_write_and_unavailable_are_explicit_not_success", "test_current_readback_and_grant_expiry_boundaries_are_stale_not_shape_errors", "test_exact_predecessor_registration_selection_is_structural_but_stale", "test_well_formed_future_publication_is_stale_not_fixture_shape_error"),
        "REPLAY": ("test_replay_fixed_point_detects_second_registered_same_output_coordinate", "test_unknown_registration_cannot_be_rewritten_into_registered_result", "test_historical_same_request_result_reached_by_successor_is_conflict"),
        "PAIR": ("test_q2_pair_exact_twenty_one_record_closure_builds_nonlive_handoff", "test_pair_missing_typed_root_is_pair_mismatch", "test_pair_malformed_typed_roots_fail_before_pair_evaluation", "test_each_pair_branch_nonconsistent_observation_has_no_handoff"),
        "NO_EFFECT": ("test_wire_digest_current_and_no_effect", "test_pure_api_effect_tripwires_cover_parser_assessment_and_handoff", "test_public_api_has_no_pair_or_live_parameter"),
        "PRIVACY": ("test_hostile_parse_failure_has_fixed_code_without_chained_payload_echo", "test_unbound_nominal_readers_reject_before_hostile_hooks", "test_all_nominal_readers_and_copy_paths_preserve_detached_issued_bodies"),
        "COMPAT": ("test_schema_mirror_is_exact_and_root_mentions_all_contract_variants", "test_r2_pinned_schema_resource_is_byte_exact_and_has_all_four_fixture_identifier_arms"),
    }
    assert set(coverage) == {"WIRE", "DIGEST", "ROLE", "IDENTITY", "CUSTODY", "CURRENT", "REPLAY", "PAIR", "NO_EFFECT", "PRIVACY", "COMPAT"}
    assert all(name in globals() for tests in coverage.values() for name in tests)


def test_public_api_has_no_pair_or_live_parameter() -> None:
    payload, r = raw_bundle()
    bundle = parse_fixture_bundle(canonical_json_bytes(payload))
    with pytest.raises(Task089ContractError):
        build_q2_pair_handoff_fixture(bundle, processed_request_sha256=r["R"]["record_sha256"], processed_readback_sha256=r["O"]["record_sha256"], copy_request_sha256=r["R"]["record_sha256"], copy_readback_sha256=r["O"]["record_sha256"])


def test_replay_fixed_point_detects_second_registered_same_output_coordinate() -> None:
    payload, r = raw_bundle()
    request = dict(r["R"])
    request["adoption_operation_id"] = "OP-33333333333333333333333333"
    request["expected_registry_generation"] = 1
    request["semantic_key_sha256"] = semantic_key(request)
    request = own("Task089AdoptionRequestFixtureV1", request)
    snapshot = dict(r["A"]["asset_snapshot"])
    snapshot["asset_id"] = "ASSET-44444444444444444444444444"
    snapshot["producer_operation_id"] = request["adoption_operation_id"]
    snapshot["logical_uri"] = "asset://JOB-00000000000000000000000000/owner-voice/raw_capture/ASSET-44444444444444444444444444"
    registration = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=request["record_sha256"], outcome="REGISTERED", registry_generation=2, asset_snapshot=snapshot))
    payload["records"].extend([request, registration])
    payload["bundle_sha256"] = bundle_digest(payload)
    assessment = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R"]["record_sha256"], readback_sha256=r["O"]["record_sha256"])
    assert (assessment.fixture_state, assessment.reason_code) == ("CONFLICT", "SEMANTIC_CONFLICT")


def test_selected_same_request_registration_is_structural_then_conflict() -> None:
    payload, r = raw_bundle()
    alternate_snapshot = dict(r["A"]["asset_snapshot"])
    alternate_snapshot["asset_id"] = "ASSET-AAAAAAAAAAAAAAAAAAAAAAAAAA"
    alternate_snapshot["logical_uri"] = "asset://JOB-00000000000000000000000000/owner-voice/raw_capture/ASSET-AAAAAAAAAAAAAAAAAAAAAAAAAA"
    alternate = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=r["R"]["record_sha256"], outcome="REGISTERED", registry_generation=1, asset_snapshot=alternate_snapshot))
    readback = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=r["R"]["record_sha256"], registration_sha256=r["A"]["record_sha256"], observation_kind="SNAPSHOT", observed_subject_sha256=r["S"]["record_sha256"], observed_grant_sha256=r["G"]["record_sha256"], observed_registry_generation=1, selected_asset_id=alternate_snapshot["asset_id"], selected_registration_sha256=alternate["record_sha256"], observed_custody_sha256=r["CU"]["record_sha256"], fixture_session="fixture-session", observed_at=T2, fresh_until=T9))
    payload["records"] = [r["S"], r["G"], r["P"], r["CU"], r["R"], r["A"], alternate, readback]
    payload["bundle_sha256"] = bundle_digest(payload)
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R"]["record_sha256"], readback_sha256=readback["record_sha256"])
    assert (result.fixture_state, result.reason_code) == ("CONFLICT", "SEMANTIC_CONFLICT")


def test_unknown_registration_cannot_be_rewritten_into_registered_result() -> None:
    payload, records = raw_bundle(outcome="COMPLETION_UNKNOWN", observation="UNRESOLVED")
    snapshot = {"asset_id":"ASSET-DDDDDDDDDDDDDDDDDDDDDDDDDD", "production_job_id":records["S"]["production_job_id"], "asset_type":"AUDIO", "asset_role":"RAW_CAPTURE", "logical_uri":"asset://JOB-00000000000000000000000000/owner-voice/raw_capture/ASSET-DDDDDDDDDDDDDDDDDDDDDDDDDD", "checksum":records["P"]["content_sha256"], "asset_version":1, "producer_operation_id":records["R"]["adoption_operation_id"], "custody_receipt_sha256":records["CU"]["custody_receipt"]["receipt_sha256"]}
    registered = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=records["R"]["record_sha256"], outcome="REGISTERED", registry_generation=1, asset_snapshot=snapshot))
    payload["records"].append(registered)
    payload["bundle_sha256"] = bundle_digest(payload)
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=records["R"]["record_sha256"], readback_sha256=records["O"]["record_sha256"])
    assert (result.fixture_state, result.reason_code) == ("CONFLICT", "SEMANTIC_CONFLICT")


def test_exact_predecessor_registration_selection_is_structural_but_stale() -> None:
    payload, records = later_raw_generation_bundle()
    selected = records["A1"]
    readback = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=records["R2"]["record_sha256"], registration_sha256=records["A2"]["record_sha256"], observation_kind="SNAPSHOT", observed_subject_sha256=records["S"]["record_sha256"], observed_grant_sha256=records["G"]["record_sha256"], observed_registry_generation=selected["registry_generation"], selected_asset_id=selected["asset_snapshot"]["asset_id"], selected_registration_sha256=selected["record_sha256"], observed_custody_sha256=records["CU1"]["record_sha256"], fixture_session="fixture-session", observed_at=T2, fresh_until=T9))
    payload["records"][-1] = readback
    payload["bundle_sha256"] = bundle_digest(payload)
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=records["R2"]["record_sha256"], readback_sha256=readback["record_sha256"])
    assert (result.fixture_state, result.reason_code) == ("STALE", "CURRENTNESS_MISMATCH")


def test_selected_registration_from_distinct_lineage_is_reference_mismatch() -> None:
    payload, records = raw_bundle()
    foreign, foreign_records = raw_bundle(project_id="fixture-other")
    readback = own(
        "Task089CurrentReadbackFixtureV1",
        common(
            "Task089CurrentReadbackFixtureV1",
            request_sha256=records["R"]["record_sha256"],
            registration_sha256=records["A"]["record_sha256"],
            observation_kind="SNAPSHOT",
            observed_subject_sha256=records["S"]["record_sha256"],
            observed_grant_sha256=records["G"]["record_sha256"],
            observed_registry_generation=foreign_records["A"]["registry_generation"],
            selected_asset_id=foreign_records["A"]["asset_snapshot"]["asset_id"],
            selected_registration_sha256=foreign_records["A"]["record_sha256"],
            observed_custody_sha256=records["CU"]["record_sha256"],
            fixture_session="fixture-session",
            observed_at=T2,
            fresh_until=T9,
        ),
    )
    payload["records"] = [
        records["S"], records["G"], records["P"], records["CU"], records["R"], records["A"],
        *foreign["records"][:-1],
        readback,
    ]
    payload["bundle_sha256"] = bundle_digest(payload)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code == "REFERENCE_MISMATCH"


@pytest.mark.parametrize("missing", ["processed_request_sha256", "processed_readback_sha256", "copy_request_sha256", "copy_readback_sha256"])
def test_pair_missing_typed_root_is_pair_mismatch(missing: str) -> None:
    payload, branches = q2_pair_bundle()
    values = {
        "processed_request_sha256": branches["P"]["R"]["record_sha256"],
        "processed_readback_sha256": branches["P"]["O"]["record_sha256"],
        "copy_request_sha256": branches["C"]["R"]["record_sha256"],
        "copy_readback_sha256": branches["C"]["O"]["record_sha256"],
    }
    values[missing] = h("absent-" + missing)
    with pytest.raises(Task089ContractError) as exc:
        build_q2_pair_handoff_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), **values)
    assert exc.value.code == "PAIR_MISMATCH"


@pytest.mark.parametrize("malformed", ["processed_request_sha256", "processed_readback_sha256", "copy_request_sha256", "copy_readback_sha256"])
def test_pair_malformed_typed_roots_fail_before_pair_evaluation(malformed: str) -> None:
    payload, branches = q2_pair_bundle()
    values = {"processed_request_sha256":branches["P"]["R"]["record_sha256"], "processed_readback_sha256":branches["P"]["O"]["record_sha256"], "copy_request_sha256":branches["C"]["R"]["record_sha256"], "copy_readback_sha256":branches["C"]["O"]["record_sha256"]}
    values[malformed] = "not-a-digest"
    with pytest.raises(Task089ContractError) as exc:
        build_q2_pair_handoff_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), **values)
    assert exc.value.code == "MALFORMED_FIXTURE"


@pytest.mark.parametrize("branch", ["processed", "copy"])
@pytest.mark.parametrize("outcome,observation", [("REJECTED_NO_WRITE", "NO_WRITE"), ("COMPLETION_UNKNOWN", "UNRESOLVED"), ("REGISTERED", "UNAVAILABLE"), ("REGISTERED", "RESTARTED")])
def test_each_pair_branch_nonconsistent_observation_has_no_handoff(branch: str, outcome: str, observation: str) -> None:
    options = {f"{branch}_outcome": outcome, f"{branch}_observation": observation}
    payload, branches = q2_pair_bundle(**options)
    bundle = parse_fixture_bundle(canonical_json_bytes(payload))
    with pytest.raises(Task089ContractError) as exc:
        build_q2_pair_handoff_fixture(bundle, processed_request_sha256=branches["P"]["R"]["record_sha256"], processed_readback_sha256=branches["P"]["O"]["record_sha256"], copy_request_sha256=branches["C"]["R"]["record_sha256"], copy_readback_sha256=branches["C"]["O"]["record_sha256"])
    assert exc.value.code == "PAIR_MISMATCH"


@pytest.mark.parametrize("branch", ["P", "C"])
def test_each_pair_branch_stale_observation_has_no_handoff(branch: str) -> None:
    payload, branches = q2_pair_bundle()
    stale = own("Task089CurrentReadbackFixtureV1", dict(branches[branch]["O"], observed_at=T1, fresh_until=T2))
    payload["records"] = [stale if item["record_sha256"] == branches[branch]["O"]["record_sha256"] else item for item in payload["records"]]
    payload["bundle_sha256"] = bundle_digest(payload)
    values = {"processed_request_sha256": branches["P"]["R"]["record_sha256"], "processed_readback_sha256": stale["record_sha256"] if branch == "P" else branches["P"]["O"]["record_sha256"], "copy_request_sha256": branches["C"]["R"]["record_sha256"], "copy_readback_sha256": stale["record_sha256"] if branch == "C" else branches["C"]["O"]["record_sha256"]}
    with pytest.raises(Task089ContractError) as exc:
        build_q2_pair_handoff_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), **values)
    assert exc.value.code == "PAIR_MISMATCH"


def test_unbound_nominal_readers_reject_before_hostile_hooks() -> None:
    class Hostile:
        touched = False
        def __hash__(self) -> int:
            Hostile.touched = True
            raise AssertionError("hook")
    for reader in (Task089AdoptionAssessment.to_dict, Task089Q2PairHandoff.to_dict, Task089FixtureBundle.to_dict):
        with pytest.raises(Task089ContractError) as exc:
            reader(Hostile())  # type: ignore[arg-type]
        assert exc.value.code == "MALFORMED_FIXTURE"
    for reader in (Task089AdoptionAssessment.__getattr__, Task089Q2PairHandoff.__getattr__, Task089FixtureBundle.__getattr__):
        with pytest.raises(Task089ContractError) as exc:
            reader(Hostile(), "forged")  # type: ignore[arg-type]
        assert exc.value.code == "MALFORMED_FIXTURE"
    assert Hostile.touched is False


@pytest.mark.parametrize("record_index,field,value", [
    (0, "fixture_case", "case-without-fixture-prefix"),
    (1, "q1_readback_sha256", h("capture-grant-must-be-null")),
    (2, "record_type", ["Task089ProducerOutputFixtureV1"]),
])
def test_local_pinned_schema_admission_rejects_closed_role_and_discriminator_arms(record_index: int, field: str, value: object) -> None:
    payload, _ = raw_bundle()
    payload["records"][record_index][field] = value
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code == "MALFORMED_FIXTURE"


@pytest.mark.parametrize("field,wrong_type", [
    ("observed_subject_sha256", "G"),
    ("observed_grant_sha256", "S"),
    ("observed_custody_sha256", "S"),
])
@pytest.mark.parametrize("missing", [False, True])
def test_observed_owner_references_are_total_and_typed(field: str, wrong_type: str, missing: bool) -> None:
    payload, r = raw_bundle()
    readback = dict(r["O"])
    readback[field] = h("missing-" + field) if missing else r[wrong_type]["record_sha256"]
    readback = own("Task089CurrentReadbackFixtureV1", readback)
    payload["records"][-1] = readback
    payload["bundle_sha256"] = bundle_digest(payload)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code == "REFERENCE_MISMATCH"


@pytest.mark.parametrize("reverse_records", [False, True])
def test_expired_owner_windows_are_assessment_stale_not_parser_shape(reverse_records: bool) -> None:
    payload, r = raw_bundle()
    payload["observed_at"] = T9
    if reverse_records:
        payload["records"] = list(reversed(payload["records"]))
    payload["bundle_sha256"] = bundle_digest(payload)
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R"]["record_sha256"], readback_sha256=r["O"]["record_sha256"])
    assert (result.fixture_state, result.reason_code) == ("STALE", "CURRENTNESS_MISMATCH")


@pytest.mark.parametrize("reverse_records", [False, True])
def test_historical_same_request_result_reached_by_successor_is_conflict(reverse_records: bool) -> None:
    payload, r = later_raw_generation_bundle()
    alternate_snapshot = dict(r["A1"]["asset_snapshot"])
    alternate_snapshot["asset_id"] = "ASSET-BBBBBBBBBBBBBBBBBBBBBBBBBB"
    alternate_snapshot["logical_uri"] = "asset://JOB-00000000000000000000000000/owner-voice/raw_capture/ASSET-BBBBBBBBBBBBBBBBBBBBBBBBBB"
    alternate = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=r["R1"]["record_sha256"], outcome="REGISTERED", registry_generation=1, asset_snapshot=alternate_snapshot))
    payload["records"].append(alternate)
    if reverse_records:
        payload["records"] = list(reversed(payload["records"]))
    payload["bundle_sha256"] = bundle_digest(payload)
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R2"]["record_sha256"], readback_sha256=r["O2"]["record_sha256"])
    assert (result.fixture_state, result.reason_code) == ("CONFLICT", "SEMANTIC_CONFLICT")


@pytest.mark.parametrize("new_operation,new_expected", [(True, 0), (False, 1)])
@pytest.mark.parametrize("reverse_records", [False, True])
def test_historical_different_request_semantic_and_same_output_contenders_conflict(new_operation: bool, new_expected: int, reverse_records: bool) -> None:
    payload, r = later_raw_generation_bundle()
    request = dict(r["R1"], expected_registry_generation=new_expected, semantic_key_sha256=None)
    if new_operation:
        request["adoption_operation_id"] = "OP-DDDDDDDDDDDDDDDDDDDDDDDDDD"
    request["semantic_key_sha256"] = semantic_key(request)
    request = own("Task089AdoptionRequestFixtureV1", request)
    snapshot = dict(r["A1"]["asset_snapshot"], asset_id="ASSET-CCCCCCCCCCCCCCCCCCCCCCCCCC", producer_operation_id=request["adoption_operation_id"])
    snapshot["logical_uri"] = "asset://JOB-00000000000000000000000000/owner-voice/raw_capture/" + snapshot["asset_id"]
    alternate = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=request["record_sha256"], outcome="REGISTERED", registry_generation=new_expected + 1, asset_snapshot=snapshot))
    payload["records"].extend([request, alternate])
    if reverse_records:
        payload["records"] = list(reversed(payload["records"]))
    payload["bundle_sha256"] = bundle_digest(payload)
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(payload)), request_sha256=r["R2"]["record_sha256"], readback_sha256=r["O2"]["record_sha256"])
    assert (result.fixture_state, result.reason_code) == ("CONFLICT", "SEMANTIC_CONFLICT")


def test_all_nominal_types_reject_public_body_mutation_and_keep_detached_views() -> None:
    raw, r = raw_bundle()
    assessment = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(raw)), request_sha256=r["R"]["record_sha256"], readback_sha256=r["O"]["record_sha256"])
    pair, branches = q2_pair_bundle()
    bundle = parse_fixture_bundle(canonical_json_bytes(pair))
    handoff = build_q2_pair_handoff_fixture(bundle, processed_request_sha256=branches["P"]["R"]["record_sha256"], processed_readback_sha256=branches["P"]["O"]["record_sha256"], copy_request_sha256=branches["C"]["R"]["record_sha256"], copy_readback_sha256=branches["C"]["O"]["record_sha256"])
    class HostileName:
        touched = False
        def __hash__(self) -> int:
            HostileName.touched = True
            raise AssertionError("name hook")
    for nominal in (assessment, bundle, handoff):
        before = nominal.to_dict()
        with pytest.raises(Task089ContractError) as exc:
            nominal._body = b"{}"  # type: ignore[attr-defined]
        assert exc.value.code == "MALFORMED_FIXTURE"
        with pytest.raises(Task089ContractError) as exc:
            del nominal._body  # type: ignore[attr-defined]
        assert exc.value.code == "MALFORMED_FIXTURE"
        with pytest.raises(Task089ContractError) as exc:
            type(nominal).__getattr__(nominal, HostileName())  # type: ignore[arg-type]
        assert exc.value.code == "MALFORMED_FIXTURE"
        assert nominal.to_dict() == before
    assert HostileName.touched is False


def test_decoder_and_bundle_cardinality_limits_fail_before_any_fixture_claim() -> None:
    payload, r = raw_bundle()
    payload["records"] = [r["S"]] * 257
    payload["bundle_sha256"] = bundle_digest(payload)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code == "MALFORMED_FIXTURE"


@pytest.mark.parametrize("field", ["opened_physical_identity_sha256", "cipher_backend_identity_sha256"])
def test_resealed_receipt_publication_identity_mismatch_fails_but_matching_control_passes(field: str) -> None:
    payload, records = raw_bundle()
    changed = h("resealed-event-" + field)
    matching, matching_records = reseal_raw_publication(payload, records, event_updates={field: changed})
    good = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(matching)), request_sha256=matching_records["R"]["record_sha256"], readback_sha256=matching_records["O"]["record_sha256"])
    assert good.fixture_state == "CONSISTENT_REGISTERED"
    mismatched, _ = reseal_raw_publication(payload, records, event_updates={field: changed}, receipt_overrides={field: records["CU"]["custody_receipt"][field]})
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(mismatched))
    assert exc.value.code == "REFERENCE_MISMATCH"


def test_well_formed_future_publication_is_stale_not_fixture_shape_error() -> None:
    payload, records = raw_bundle()
    future, updated = reseal_raw_publication(payload, records, event_updates={"created_at": T3, "observed_at": T3})
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(future)), request_sha256=updated["R"]["record_sha256"], readback_sha256=updated["O"]["record_sha256"])
    assert (result.fixture_state, result.reason_code) == ("STALE", "CURRENTNESS_MISMATCH")


def test_nonmonotonic_later_event_is_reference_mismatch_even_when_prefix_is_expired() -> None:
    payload, records = raw_bundle()
    first = records["CU"]["generation_events"][0]
    tombstone = PrivateMediaGenerationEvent.create(
        event_kind=GenerationEventKind.GENERATION_REVOKED, logical_slot_ref=first["logical_slot_ref"], artifact_class=ArtifactClass(first["artifact_class"]), event_revision=2, predecessor_event_sha256=first["event_sha256"], owner_subject_revision_sha256=first["owner_subject_revision_sha256"], purpose=first["purpose"], consent_rights_revision_sha256=first["consent_rights_revision_sha256"], created_at=T0, observed_at=T0, fresh_until=T9, trusted_time_binding_sha256=h("nonmonotonic-time"), published_generation_revision=None, opaque_artifact_id=None, custody_binding_sha256=None, content_sha256=None, media_metadata_sha256=None, opened_physical_identity_sha256=None, cipher_backend_identity_sha256=None, target_generation_revision=1, target_publish_event_sha256=first["event_sha256"], tombstone_decision_sha256=h("nonmonotonic-tombstone"),
    ).as_dict()
    custody = own("Task089CustodyFixtureV1", common("Task089CustodyFixtureV1", producer_sha256=records["P"]["record_sha256"], custody_receipt=records["CU"]["custody_receipt"], generation_events=[first, tombstone]))
    request = dict(records["R"], custody_sha256=custody["record_sha256"], semantic_key_sha256=None); request["semantic_key_sha256"] = semantic_key(request); request = own("Task089AdoptionRequestFixtureV1", request)
    snapshot = dict(records["A"]["asset_snapshot"])
    registration = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=request["record_sha256"], outcome="REGISTERED", registry_generation=1, asset_snapshot=snapshot))
    readback = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=request["record_sha256"], registration_sha256=registration["record_sha256"], observation_kind="SNAPSHOT", observed_subject_sha256=records["S"]["record_sha256"], observed_grant_sha256=records["G"]["record_sha256"], observed_registry_generation=1, selected_asset_id=snapshot["asset_id"], selected_registration_sha256=registration["record_sha256"], observed_custody_sha256=custody["record_sha256"], fixture_session="fixture-session", observed_at=T2, fresh_until=T9))
    payload["records"] = [records["S"], records["G"], records["P"], custody, request, registration, readback]
    payload["observed_at"] = T9
    payload["bundle_sha256"] = bundle_digest(payload)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code == "REFERENCE_MISMATCH"


@pytest.mark.parametrize("field", ["opened_physical_identity_sha256", "cipher_backend_identity_sha256"])
def test_historical_resealed_receipt_publication_identity_is_checked_through_successor(field: str) -> None:
    """Rebuild CU1→R1/A1→CU2→R2/A2/O2 so only the old owner join differs."""
    payload, r = later_raw_generation_bundle()
    foreign = {"record_type", "schema_version", "canonical_owner_task", "event_sha256"}
    def publication(source: dict[str, object], **updates: object) -> dict[str, object]:
        values = {key: value for key, value in source.items() if key not in foreign}
        values.update(updates)
        values["custody_binding_sha256"] = custody_staged_binding_sha256(
            opaque_artifact_id=values["opaque_artifact_id"], logical_slot_ref=values["logical_slot_ref"], generation_revision=values["published_generation_revision"], owner_subject_revision_sha256=values["owner_subject_revision_sha256"], purpose=values["purpose"], artifact_class=values["artifact_class"], content_sha256=values["content_sha256"], media_metadata_sha256=values["media_metadata_sha256"], opened_physical_identity_sha256=values["opened_physical_identity_sha256"], cipher_backend_identity_sha256=values["cipher_backend_identity_sha256"], consent_rights_revision_sha256=values["consent_rights_revision_sha256"], observed_at=values["observed_at"], fresh_until=values["fresh_until"],
        )
        return PrivateMediaGenerationEvent.create(**values).as_dict()
    def receipt(event: dict[str, object], predecessor: str | None, **overrides: object) -> dict[str, object]:
        values = {key: event[key] for key in ("opaque_artifact_id", "logical_slot_ref", "owner_subject_revision_sha256", "purpose", "artifact_class", "content_sha256", "media_metadata_sha256", "opened_physical_identity_sha256", "cipher_backend_identity_sha256", "consent_rights_revision_sha256", "observed_at", "fresh_until")}
        values.update(generation_revision=event["published_generation_revision"], predecessor_receipt_sha256=predecessor, generation_event_sha256=event["event_sha256"], event_head_sha256=event["event_sha256"])
        values.update(overrides)
        values["custody_binding_sha256"] = custody_staged_binding_sha256(
            opaque_artifact_id=values["opaque_artifact_id"], logical_slot_ref=values["logical_slot_ref"], generation_revision=values["generation_revision"], owner_subject_revision_sha256=values["owner_subject_revision_sha256"], purpose=values["purpose"], artifact_class=values["artifact_class"], content_sha256=values["content_sha256"], media_metadata_sha256=values["media_metadata_sha256"], opened_physical_identity_sha256=values["opened_physical_identity_sha256"], cipher_backend_identity_sha256=values["cipher_backend_identity_sha256"], consent_rights_revision_sha256=values["consent_rights_revision_sha256"], observed_at=values["observed_at"], fresh_until=values["fresh_until"],
        )
        return PrivateMediaCustodyReceipt.create(**values).as_dict()
    changed_one = publication(r["CU1"]["generation_events"][0], **{field: h("historical-event-" + field)})
    matching_one = receipt(changed_one, None)
    two = publication(r["CU2"]["generation_events"][-1], predecessor_event_sha256=changed_one["event_sha256"])
    def rebuild(old_receipt: dict[str, object]) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
        receipt_two = receipt(two, old_receipt["receipt_sha256"])
        cu1 = own("Task089CustodyFixtureV1", common("Task089CustodyFixtureV1", producer_sha256=r["P1"]["record_sha256"], custody_receipt=old_receipt, generation_events=[changed_one]))
        r1 = dict(r["R1"], custody_sha256=cu1["record_sha256"], semantic_key_sha256=None); r1["semantic_key_sha256"] = semantic_key(r1); r1 = own("Task089AdoptionRequestFixtureV1", r1)
        a1_snapshot = dict(r["A1"]["asset_snapshot"], custody_receipt_sha256=old_receipt["receipt_sha256"])
        a1 = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=r1["record_sha256"], outcome="REGISTERED", registry_generation=1, asset_snapshot=a1_snapshot))
        cu2 = own("Task089CustodyFixtureV1", common("Task089CustodyFixtureV1", producer_sha256=r["P2"]["record_sha256"], custody_receipt=receipt_two, generation_events=[changed_one, two]))
        r2 = dict(r["R2"], custody_sha256=cu2["record_sha256"], predecessor_registration_sha256=a1["record_sha256"], semantic_key_sha256=None); r2["semantic_key_sha256"] = semantic_key(r2); r2 = own("Task089AdoptionRequestFixtureV1", r2)
        a2_snapshot = dict(r["A2"]["asset_snapshot"], custody_receipt_sha256=receipt_two["receipt_sha256"])
        a2 = own("Task089RegistrationFixtureV1", common("Task089RegistrationFixtureV1", request_sha256=r2["record_sha256"], outcome="REGISTERED", registry_generation=2, asset_snapshot=a2_snapshot))
        o2 = own("Task089CurrentReadbackFixtureV1", common("Task089CurrentReadbackFixtureV1", request_sha256=r2["record_sha256"], registration_sha256=a2["record_sha256"], observation_kind="SNAPSHOT", observed_subject_sha256=r["S"]["record_sha256"], observed_grant_sha256=r["G"]["record_sha256"], observed_registry_generation=2, selected_asset_id=a2_snapshot["asset_id"], selected_registration_sha256=a2["record_sha256"], observed_custody_sha256=cu2["record_sha256"], fixture_session="fixture-session", observed_at=T2, fresh_until=T9))
        replacement = {r["CU1"]["record_sha256"]:cu1, r["R1"]["record_sha256"]:r1, r["A1"]["record_sha256"]:a1, r["CU2"]["record_sha256"]:cu2, r["R2"]["record_sha256"]:r2, r["A2"]["record_sha256"]:a2, r["O2"]["record_sha256"]:o2}
        result = dict(payload, records=[replacement.get(record["record_sha256"], record) for record in payload["records"]])
        result["bundle_sha256"] = bundle_digest(result)
        return result, {"R2":r2, "O2":o2}
    control, roots = rebuild(matching_one)
    result = assess_adoption_fixture(parse_fixture_bundle(canonical_json_bytes(control)), request_sha256=roots["R2"]["record_sha256"], readback_sha256=roots["O2"]["record_sha256"])
    assert result.fixture_state == "CONSISTENT_REGISTERED"
    mismatched_one = receipt(changed_one, None, **{field:r["CU1"]["custody_receipt"][field]})
    bad, _ = rebuild(mismatched_one)
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(bad))
    assert exc.value.code == "REFERENCE_MISMATCH"
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(b'{"x":"' + b"a" * 1_048_576 + b'"}')
    assert exc.value.code == "MALFORMED_FIXTURE"


@pytest.mark.parametrize("mutation", ["wrong-role", "bad-digest", "bool-generation", "expired-observation"])
def test_role_digest_integer_and_currentness_faults_fail_closed(mutation: str) -> None:
    payload, _ = raw_bundle()
    if mutation == "wrong-role":
        payload["records"][2]["asset_role"] = "TRAINING_COPY"
    elif mutation == "bad-digest":
        payload["records"][3]["producer_sha256"] = h("unrelated")
    elif mutation == "bool-generation":
        payload["records"][4]["expected_registry_generation"] = True
    else:
        payload["records"][6]["fresh_until"] = T2
    with pytest.raises(Task089ContractError) as exc:
        parse_fixture_bundle(canonical_json_bytes(payload))
    assert exc.value.code in {"MALFORMED_FIXTURE", "REFERENCE_MISMATCH", "ROLE_MISMATCH"}
