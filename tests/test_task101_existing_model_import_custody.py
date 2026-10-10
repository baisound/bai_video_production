from __future__ import annotations

import copy
import json
from pathlib import Path
import pickle

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task101_existing_model_import_custody import (
    ExistingModelImportCapabilityAuditV1,
    ExistingModelImportCustodyReadbackV1,
    ExistingModelImportCustodyReceiptV1,
    ExistingModelImportIntentV1,
    FakeExistingModelImportCustodyBackend,
    FixtureOnlyRecordRef,
    MAX_JSON_BYTES,
    NativeImportBoundary,
    NativeImportTerminalResult,
    classify_native_import_boundary,
    create_existing_model_import_capability_audit,
    create_existing_model_import_custody_receipt,
    create_existing_model_import_intent,
    evaluate_existing_model_import_custody_readback,
    parse_existing_model_import_json,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "task101-existing-model-import-custody.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name

DOMAINS = {
    "intent_sha256": b"bai-video-production/task101/existing-model-import-intent/v1\0",
    "receipt_sha256": b"bai-video-production/task101/existing-model-import-custody-receipt/v1\0",
    "readback_sha256": b"bai-video-production/task101/existing-model-import-custody-readback/v1\0",
    "audit_sha256": b"bai-video-production/task101/existing-model-import-capability-audit/v1\0",
}


def h(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def rehash(body: dict, field: str) -> dict:
    result = copy.deepcopy(body)
    result.pop(field, None)
    body[field] = sha256_bytes(DOMAINS[field] + canonical_json_bytes(result))
    return body


def artifact(role: str) -> dict:
    return {
        "role": role,
        "content_sha256": h(f"{role}-content"),
        "byte_count": 101 if role == "SOVITS" else 202,
        "opaque_source_identity_sha256": h(f"{role}-source"),
    }


def make_intent(**changes):
    fields = {
        "import_intent_id": "intent-1",
        "revision": 1,
        "predecessor_sha256": None,
        "project_manifest_sha256": h("project"),
        "voice_profile_revision_sha256": h("voice-profile"),
        "model_candidate_revision_sha256": h("candidate"),
        "model_artifact_binding_sha256": h("binding"),
        "h4_approval_sha256": h("h4"),
        "consent_currentness_sha256": h("consent"),
        "rights_currentness_sha256": h("rights"),
        "license_evidence_sha256": h("license"),
        "historical_provenance_reconciliation_sha256": h("history"),
        "provider_id": "local-owner-voice",
        "engine_id": "gpt-sovits-v2pro",
        "model_id": "owner-c04",
        "runtime_build_sha256": h("runtime"),
        "model_pair_sha256": h("pair"),
        "artifacts": [artifact("SOVITS"), artifact("GPT")],
        "protected_destination_class": "BVP_OWNER_VOICE_MODEL_CUSTODY_V1",
        "cipher_policy_sha256": h("cipher-policy"),
        "key_scope_sha256": h("key-scope"),
        "principal_access_policy_sha256": h("principal"),
        "retention_policy_sha256": h("retention"),
        "revocation_policy_sha256": h("revocation"),
        "human_import_authority_sha256": h("human-authority"),
        "issued_at": "2026-10-10T00:00:00Z",
        "evaluated_at": "2026-10-10T00:00:01Z",
        "expires_at": "2026-10-10T01:00:00Z",
    }
    fields.update(changes)
    return create_existing_model_import_intent(**fields)


def receipt_artifact(item: dict) -> dict:
    role = item["role"]
    return {
        "role": role,
        "content_sha256": item["content_sha256"],
        "plaintext_byte_count": item["byte_count"],
        "source_physical_identity_sha256": h(f"{role}-source-physical"),
        "ciphertext_sha256": h(f"{role}-ciphertext"),
        "ciphertext_byte_count": item["byte_count"] + 16,
        "destination_physical_identity_sha256": h(f"{role}-destination-physical"),
    }


def make_receipt(intent=None, **changes):
    intent = intent or make_intent()
    i = intent.to_dict()
    fields = {
        "operation_id": "operation-1",
        "import_intent_id": i["import_intent_id"],
        "intent_sha256": i["intent_sha256"],
        "project_manifest_sha256": i["project_manifest_sha256"],
        "voice_profile_revision_sha256": i["voice_profile_revision_sha256"],
        "model_candidate_revision_sha256": i["model_candidate_revision_sha256"],
        "model_artifact_binding_sha256": i["model_artifact_binding_sha256"],
        "model_pair_sha256": i["model_pair_sha256"],
        "runtime_build_sha256": i["runtime_build_sha256"],
        "source_physical_identity_set_sha256": h("source-set"),
        "destination_instance_sha256": h("destination"),
        "sealed_inventory_sha256": h("sealed-inventory"),
        "artifacts": [receipt_artifact(item) for item in i["artifacts"]],
        "cipher_backend_sha256": h("cipher-backend"),
        "cipher_policy_sha256": i["cipher_policy_sha256"],
        "key_scope_sha256": i["key_scope_sha256"],
        "principal_access_policy_sha256": i["principal_access_policy_sha256"],
        "import_event_chain_head_sha256": h("event-chain"),
        "seal_receipt_sha256": h("seal"),
        "durability_receipt_sha256": h("durability"),
        "physical_readback_sha256": h("physical-readback"),
        "started_at": "2026-10-10T00:02:00Z",
        "sealed_at": "2026-10-10T00:03:00Z",
        "read_back_at": "2026-10-10T00:04:00Z",
        "expires_at": "2026-10-10T01:00:00Z",
        "completion_state": "SEALED_CURRENT",
    }
    fields.update(changes)
    return create_existing_model_import_custody_receipt(**fields)


def make_readback(receipt=None, **changes):
    receipt = receipt or make_receipt()
    r = receipt.to_dict()
    fields = {
        "readback_id": "readback-1",
        "custody_generation": 1,
        "current_inventory_sha256": r["sealed_inventory_sha256"],
        "current_physical_identity_set_sha256": h("current-physical-set"),
        "observed_model_pair_sha256": r["model_pair_sha256"],
        "observed_runtime_build_sha256": r["runtime_build_sha256"],
        "revocation_state": "NOT_REVOKED",
        "evaluated_at": "2026-10-10T00:05:00Z",
        "expires_at": "2026-10-10T00:10:00Z",
        "physical_identity_matches": True,
    }
    fields.update(changes)
    return evaluate_existing_model_import_custody_readback(receipt, **fields)


def make_audit(readback=None, predecessor=None, **changes):
    readback = readback or make_readback()
    fields = {
        "capability_id": "capability-1",
        "operation_id": "observe-operation-1",
        "purpose": "INSTALLED_IDENTITY_OBSERVATION",
        "consumer_task": "TASK-100",
        "custody_readback_sha256": readback.readback_sha256,
        "model_pair_sha256": readback.to_dict()["model_pair_sha256"],
        "state": "ISSUED" if predecessor is None else "OPEN_STARTED",
        "predecessor_sha256": None if predecessor is None else predecessor.audit_sha256,
        "issued_at": "2026-10-10T00:06:00Z",
        "expires_at": "2026-10-10T00:09:00Z",
        "transitioned_at": "2026-10-10T00:06:00Z" if predecessor is None else "2026-10-10T00:07:00Z",
        "completed_at": None,
    }
    fields.update(changes)
    return create_existing_model_import_capability_audit(predecessor=predecessor, **fields)


def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_all_record_types_round_trip_strict_parser_and_schema() -> None:
    intent = make_intent()
    receipt = make_receipt(intent)
    readback = make_readback(receipt)
    issued = make_audit(readback)
    opened = make_audit(readback, issued)
    records = [intent, receipt, readback, issued]
    for record in records:
        body = record.to_dict()
        validator().validate(body)
        parsed = parse_existing_model_import_json(canonical_json_bytes(body))
        assert type(parsed) is type(record)
        assert parsed.to_dict() == body
    validator().validate(opened.to_dict())
    assert parse_existing_model_import_json(
        canonical_json_bytes(opened.to_dict()), predecessor=issued
    ).to_dict() == opened.to_dict()


def test_schema_mirror_is_byte_identical_and_closed() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    for definition in schema["$defs"].values():
        if definition.get("type") == "object":
            assert definition["additionalProperties"] is False
    body = make_intent().to_dict()
    body["unknown"] = True
    assert not validator().is_valid(body)


@pytest.mark.parametrize(
    "mutation, match",
    [
        (lambda b: b.update(revision=True), "PositiveInt"),
        (lambda b: b.update(predecessor_sha256=h("unexpected")), "revision 1"),
        (lambda b: b["artifacts"].reverse(), "role order"),
        (lambda b: b.update(evaluated_at=b["expires_at"]), "timestamps"),
        (lambda b: b.update(protected_destination_class="OTHER"), "destination"),
        (lambda b: b.update(provider_id=""), "valid Id"),
    ],
)
def test_intent_contract_rejects_cross_field_and_type_violations(mutation, match) -> None:
    body = make_intent().to_dict()
    mutation(body)
    rehash(body, "intent_sha256")
    with pytest.raises(ValueError, match=match):
        ExistingModelImportIntentV1.from_dict(body)


def test_digest_tamper_unknown_field_and_factory_only_immutability() -> None:
    intent = make_intent()
    body = intent.to_dict()
    body["model_id"] = "changed"
    with pytest.raises(ValueError, match="intent_sha256"):
        ExistingModelImportIntentV1.from_dict(body)
    body = intent.to_dict()
    body["unknown"] = "x"
    with pytest.raises(ValueError, match="fields are not exact"):
        ExistingModelImportIntentV1.from_dict(body)
    with pytest.raises(TypeError):
        ExistingModelImportIntentV1({})
    exported = intent.to_dict()
    exported["artifacts"][0]["role"] = "GPT"
    assert intent.to_dict()["artifacts"][0]["role"] == "SOVITS"
    with pytest.raises(TypeError):
        intent.data["model_id"] = "other"


def test_fake_backend_binds_intent_receipt_readback_and_exact_replay() -> None:
    backend = FakeExistingModelImportCustodyBackend()
    intent = make_intent()
    receipt = make_receipt(intent)
    readback = make_readback(receipt)
    intent_ref = backend.admit_intent(intent)
    assert backend.admit_intent(intent) == intent_ref
    receipt_ref = backend.admit_receipt(receipt)
    assert backend.admit_receipt(receipt) == receipt_ref
    readback_ref = backend.admit_readback(readback)
    assert readback_ref.record_sha256 == readback.readback_sha256
    crossed = make_receipt(
        intent,
        operation_id="operation-cross",
        project_manifest_sha256=h("other-project"),
    )
    with pytest.raises(ValueError, match="project_manifest_sha256"):
        backend.admit_receipt(crossed)
    replay = make_receipt(intent, operation_id=receipt.to_dict()["operation_id"], destination_instance_sha256=h("other"))
    with pytest.raises(ValueError, match="replay differs"):
        backend.admit_receipt(replay)


@pytest.mark.parametrize(
    "changes, decision, reasons",
    [
        ({}, "CURRENT", ["CURRENT"]),
        ({"current_inventory_sha256": h("other-inventory")}, "IDENTITY_MISMATCH", ["INVENTORY_MISMATCH"]),
        ({"physical_identity_matches": False}, "IDENTITY_MISMATCH", ["PHYSICAL_IDENTITY_MISMATCH"]),
        ({"observed_model_pair_sha256": h("other-pair")}, "IDENTITY_MISMATCH", ["PAIR_IDENTITY_MISMATCH"]),
        ({"observed_runtime_build_sha256": h("other-runtime")}, "IDENTITY_MISMATCH", ["RUNTIME_IDENTITY_MISMATCH"]),
        ({"revocation_state": "REVOKED"}, "REVOKED", ["REVOKED"]),
        ({"revocation_state": "UNKNOWN"}, "COMPLETION_UNKNOWN", ["REVOCATION_UNKNOWN"]),
    ],
)
def test_pure_readback_decision_matrix(changes, decision, reasons) -> None:
    body = make_readback(**changes).to_dict()
    assert body["decision"] == decision
    assert body["reason_codes"] == reasons


def test_readback_rejects_reason_order_decision_and_current_inventory_lies() -> None:
    body = make_readback().to_dict()
    body.update(decision="IDENTITY_MISMATCH", reason_codes=["RUNTIME_IDENTITY_MISMATCH", "INVENTORY_MISMATCH"])
    rehash(body, "readback_sha256")
    with pytest.raises(ValueError, match="lexicographically"):
        ExistingModelImportCustodyReadbackV1.from_dict(body)


def test_readback_evaluator_cannot_extend_or_renew_expired_receipt() -> None:
    receipt = make_receipt(expires_at="2026-10-10T00:06:00Z")
    stale = make_readback(
        receipt,
        evaluated_at="2026-10-10T00:06:00Z",
        expires_at="2026-10-10T00:06:00Z",
    )
    assert stale.to_dict()["decision"] == "STALE"
    assert stale.to_dict()["reason_codes"] == ["STALE"]
    with pytest.raises(ValueError, match="exceeds receipt authority"):
        make_readback(
            receipt,
            evaluated_at="2026-10-10T00:05:30Z",
            expires_at="2026-10-10T00:06:01Z",
        )

    backend = FakeExistingModelImportCustodyBackend()
    intent = make_intent()
    canonical_receipt = make_receipt(intent, expires_at="2026-10-10T00:06:00Z")
    backend.admit_intent(intent)
    backend.admit_receipt(canonical_receipt)
    forged = make_readback(
        canonical_receipt,
        evaluated_at="2026-10-10T00:05:00Z",
        expires_at="2026-10-10T00:06:00Z",
    ).to_dict()
    forged["expires_at"] = "2026-10-10T00:06:01Z"
    rehash(forged, "readback_sha256")
    forged_record = ExistingModelImportCustodyReadbackV1.from_dict(forged)
    with pytest.raises(ValueError, match="expiry exceeds"):
        backend.admit_readback(forged_record)


def test_readback_evaluator_requires_exact_physical_identity_boolean() -> None:
    with pytest.raises(ValueError, match="exact boolean"):
        make_readback(physical_identity_matches=1)
    body = make_readback().to_dict()
    body["current_inventory_sha256"] = h("different")
    rehash(body, "readback_sha256")
    with pytest.raises(ValueError, match="sealed inventory"):
        ExistingModelImportCustodyReadbackV1.from_dict(body)


def test_capability_audit_lifecycle_is_monotonic_one_way_and_body_free() -> None:
    backend = FakeExistingModelImportCustodyBackend()
    intent = make_intent()
    receipt = make_receipt(intent)
    readback = make_readback(receipt)
    backend.admit_intent(intent)
    backend.admit_receipt(receipt)
    backend.admit_readback(readback)
    issued = make_audit(readback)
    assert backend.admit_capability_audit(issued).record_sha256 == issued.audit_sha256
    assert backend.admit_capability_audit(issued).record_sha256 == issued.audit_sha256
    opened = make_audit(readback, issued)
    backend.admit_capability_audit(opened)
    consumed = make_audit(
        readback,
        opened,
        state="CONSUMED",
        transitioned_at="2026-10-10T00:08:00Z",
        completed_at="2026-10-10T00:08:00Z",
    )
    backend.admit_capability_audit(consumed)
    assert backend.current_audit("capability-1").record_sha256 == consumed.audit_sha256
    with pytest.raises(ValueError, match="transition"):
        make_audit(readback, consumed, state="FAILED_CLOSED", transitioned_at="2026-10-10T00:08:30Z", completed_at="2026-10-10T00:08:30Z")
    for body in (issued.to_dict(), opened.to_dict(), consumed.to_dict()):
        assert "path" not in json.dumps(body).casefold()


def test_fake_backend_rechecks_latest_readback_generation_revocation_and_expiry() -> None:
    backend = FakeExistingModelImportCustodyBackend()
    intent = make_intent()
    receipt = make_receipt(intent)
    current = make_readback(receipt, expires_at="2026-10-10T00:08:30Z")
    backend.admit_intent(intent)
    backend.admit_receipt(receipt)
    backend.admit_readback(current)
    issued = make_audit(current)
    backend.admit_capability_audit(issued)
    revoked = make_readback(
        receipt,
        readback_id="readback-2",
        custody_generation=2,
        revocation_state="REVOKED",
        evaluated_at="2026-10-10T00:06:30Z",
        expires_at="2026-10-10T00:08:30Z",
    )
    backend.admit_readback(revoked)
    old_issued = make_audit(current, capability_id="capability-old")
    with pytest.raises(ValueError, match="no longer the current"):
        backend.admit_capability_audit(old_issued)
    opened = make_audit(current, issued)
    with pytest.raises(ValueError, match="no longer the current"):
        backend.admit_capability_audit(opened)

    second_backend = FakeExistingModelImportCustodyBackend()
    second_backend.admit_intent(intent)
    second_backend.admit_receipt(receipt)
    short = make_readback(
        receipt,
        readback_id="readback-short",
        expires_at="2026-10-10T00:06:30Z",
    )
    second_backend.admit_readback(short)
    expired_issue = make_audit(
        short,
        capability_id="capability-expired",
        issued_at="2026-10-10T00:06:30Z",
        transitioned_at="2026-10-10T00:06:30Z",
    )
    with pytest.raises(ValueError, match="not current at use time"):
        second_backend.admit_capability_audit(expired_issue)


def test_fake_backend_results_are_nonserializable_fixture_only_refs() -> None:
    backend = FakeExistingModelImportCustodyBackend()
    intent = make_intent()
    ref = backend.admit_intent(intent)
    assert type(ref) is FixtureOnlyRecordRef
    assert ref.source == "FIXTURE_ONLY"
    assert ref.record_type == "ExistingModelImportIntentV1"
    assert not isinstance(ref, ExistingModelImportIntentV1)
    assert not hasattr(ref, "to_dict")
    with pytest.raises(TypeError, match="nonserializable"):
        pickle.dumps(ref)
    with pytest.raises(TypeError):
        FakeExistingModelImportCustodyBackend().admit_intent(ref)  # type: ignore[arg-type]


def test_native_failure_matrix_is_closed_effect_zero_and_complete() -> None:
    expected = {
        "BEFORE_NATIVE_EFFECT_FAILURE": "NO_EFFECT",
        "DESTINATION_PREFLIGHT_COLLISION": "NO_EFFECT",
        "SOURCE_OPENED_VALIDATION_FAILURE_CLOSED": "FAILED_CLOSED",
        "SOURCE_CLOSE_IDENTITY_UNCERTAIN": "COMPLETION_UNKNOWN",
        "OWNED_TEMPORARY_FAILURE_PROVED": "FAILED_CLOSED",
        "TEMPORARY_IDENTITY_OR_CLEANUP_UNCERTAIN": "COMPLETION_UNKNOWN",
        "FINAL_NAMESPACE_OR_DURABILITY_AMBIGUOUS": "COMPLETION_UNKNOWN",
        "SEALED_READBACK_MISMATCH": "COMPLETION_UNKNOWN",
        "COMPLETE_READBACK_CURRENT": "READBACK_CURRENT",
        "RESTART_INCOMPLETE_OR_UNTRUSTED": "COMPLETION_UNKNOWN",
    }
    assert {item.value for item in NativeImportBoundary} == set(expected)
    for boundary, result in expected.items():
        classification = classify_native_import_boundary(boundary)
        assert classification.terminal_result is NativeImportTerminalResult(result)
        assert classification.required_behavior
    with pytest.raises(ValueError, match="unsupported"):
        classify_native_import_boundary("OTHER")

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert set(schema["$defs"]["NativeImportBoundary"]["enum"]) == set(expected)
    assert set(schema["$defs"]["NativeImportTerminalResult"]["enum"]) == {
        "NO_EFFECT", "FAILED_CLOSED", "COMPLETION_UNKNOWN", "READBACK_CURRENT"
    }


def test_audit_predecessor_is_reparsed_linked_and_checked_before_monotonic_time() -> None:
    readback = make_readback()
    issued = make_audit(readback)
    opened = make_audit(readback, issued)
    backward = make_audit(
        readback,
        opened,
        state="CONSUMED",
        transitioned_at="2026-10-10T00:08:00Z",
        completed_at="2026-10-10T00:08:00Z",
    ).to_dict()
    backward["transitioned_at"] = "2026-10-10T00:06:30Z"
    backward["completed_at"] = "2026-10-10T00:06:30Z"
    rehash(backward, "audit_sha256")
    with pytest.raises(ValueError, match="moved backward"):
        ExistingModelImportCapabilityAuditV1.from_dict(backward, predecessor=opened)
    opened = make_audit(readback, issued).to_dict()
    bad_predecessor = issued.to_dict()
    bad_predecessor["audit_sha256"] = h("forged")
    with pytest.raises(ValueError, match="canonical predecessor"):
        ExistingModelImportCapabilityAuditV1.from_dict(opened, predecessor=bad_predecessor)
    opened["predecessor_sha256"] = h("wrong-link")
    rehash(opened, "audit_sha256")
    with pytest.raises(ValueError, match="exact predecessor"):
        ExistingModelImportCapabilityAuditV1.from_dict(opened, predecessor=issued)


def test_noninitial_audit_rejects_raw_or_truncated_predecessor_chain() -> None:
    readback = make_readback()
    issued = make_audit(readback)
    opened = make_audit(readback, issued)
    consumed = make_audit(
        readback,
        opened,
        state="CONSUMED",
        transitioned_at="2026-10-10T00:08:00Z",
        completed_at="2026-10-10T00:08:00Z",
    )
    forged_opened = opened.to_dict()
    forged_opened["predecessor_sha256"] = h("unavailable-predecessor")
    rehash(forged_opened, "audit_sha256")
    consumed_body = consumed.to_dict()
    consumed_body["predecessor_sha256"] = forged_opened["audit_sha256"]
    rehash(consumed_body, "audit_sha256")
    with pytest.raises(ValueError, match="canonical predecessor"):
        ExistingModelImportCapabilityAuditV1.from_dict(consumed_body, predecessor=forged_opened)
    with pytest.raises(ValueError, match="canonical predecessor"):
        parse_existing_model_import_json(
            canonical_json_bytes(consumed_body), predecessor=forged_opened
        )


def test_audit_rejects_purpose_consumer_crossing_and_immutable_change() -> None:
    readback = make_readback()
    issued = make_audit(readback)
    body = make_audit(readback, issued).to_dict()
    body["consumer_task"] = "TASK-075"
    rehash(body, "audit_sha256")
    with pytest.raises(ValueError, match="purpose"):
        ExistingModelImportCapabilityAuditV1.from_dict(body, predecessor=issued)
    body = make_audit(readback, issued).to_dict()
    body["operation_id"] = "other-operation"
    rehash(body, "audit_sha256")
    with pytest.raises(ValueError, match="immutable field"):
        ExistingModelImportCapabilityAuditV1.from_dict(body, predecessor=issued)


@pytest.mark.parametrize(
    "payload, match",
    [
        (b'{}{}', "trailing"),
        (b'\xef\xbb\xbf{}', "BOM"),
        (b'{"record_type":"x","record_type":"y"}', "duplicate"),
        (b'{"record_type":NaN}', "non-finite"),
        (b'[]', "root"),
        (b'{"record_type":"Unknown"}', "unsupported"),
    ],
)
def test_strict_parser_rejects_ambiguous_inputs(payload, match) -> None:
    with pytest.raises(ValueError, match=match):
        parse_existing_model_import_json(payload)


def test_strict_parser_limits_size_depth_nodes_arrays_and_strings() -> None:
    with pytest.raises(ValueError, match="oversized"):
        parse_existing_model_import_json(b" " * (MAX_JSON_BYTES + 1))
    too_deep: object = "leaf"
    for _ in range(18):
        too_deep = [too_deep]
    with pytest.raises(ValueError, match="depth"):
        parse_existing_model_import_json(canonical_json_bytes(too_deep))
    with pytest.raises(ValueError, match="array"):
        parse_existing_model_import_json(canonical_json_bytes([0] * 65))
    with pytest.raises(ValueError, match="string"):
        parse_existing_model_import_json(canonical_json_bytes({"record_type": "x" * 513}))


def test_schema_runtime_reject_calendar_invalid_timestamp_and_boolean_integer() -> None:
    body = make_intent().to_dict()
    body["issued_at"] = "2026-02-30T00:00:00Z"
    rehash(body, "intent_sha256")
    with pytest.raises(ValueError, match="calendar-valid"):
        ExistingModelImportIntentV1.from_dict(body)
    assert not validator().is_valid(body)
    body = make_intent().to_dict()
    body["revision"] = True
    rehash(body, "intent_sha256")
    with pytest.raises(ValueError, match="PositiveInt"):
        ExistingModelImportIntentV1.from_dict(body)
    assert not validator().is_valid(body)


def test_source_surface_has_no_native_or_external_effect_imports() -> None:
    source = (ROOT / "src" / "ai_video_production" / "task101_existing_model_import_custody.py").read_text(encoding="utf-8")
    forbidden = (
        "subprocess", "socket", "requests", "urllib", "httpx", "pathlib", "os.open",
        "open(", "ctypes", "win32", "torch", "soundfile", "librosa",
    )
    for token in forbidden:
        assert token not in source
    assert "FakeExistingModelImportCustodyBackend" in source
