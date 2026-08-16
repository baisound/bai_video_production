from __future__ import annotations

import ast
import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.assets import RetentionClass
from ai_video_production.storage_lifecycle_gc import (
    AuthorityKind,
    ContractState,
    EffectGateDecision,
    EffectResult,
    HoldState,
    LifecycleDecision,
    ObservationState,
    RetentionRule,
    StorageEffect,
    StorageEffectAuthorizationBinding,
    StorageEffectReceiptBinding,
    classify_effect_gate,
    compile_retention_policy,
    compile_storage_disposition,
    compile_storage_observation,
    public_storage_projection,
    verify_storage_record_hash,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "storage-lifecycle-gc.schema.json"
MIRROR_PATH = ROOT / "src" / "ai_video_production" / "schema_resources" / "storage-lifecycle-gc.schema.json"
MODULE_PATH = ROOT / "src" / "ai_video_production" / "storage_lifecycle_gc.py"
H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
H3 = "sha256:" + "3" * 64
T0 = "2026-08-17T00:00:00Z"
T1 = "2026-08-17T00:01:00Z"
T_ARCHIVE = "2026-08-17T00:20:00Z"
T_DELETE = "2026-08-17T00:40:00Z"
T_EXPIRES = "2026-08-17T01:00:00Z"


def rules() -> tuple[RetentionRule, ...]:
    return (
        RetentionRule(RetentionClass.STANDARD, 600, 1800),
        RetentionRule(RetentionClass.CONFIDENTIAL, 300, 1200),
        RetentionRule(RetentionClass.RESTRICTED, 120, 900),
        RetentionRule(RetentionClass.LEGAL_HOLD, None, None),
    )


def policy(**overrides):
    fields = dict(
        project_id="project-1", policy_id="retention-policy-1", revision=1,
        parent_revision_sha256=None, created_at=T0,
        max_observation_age_seconds=7200, rules=rules(),
    )
    fields.update(overrides)
    return compile_retention_policy(**fields)


def observation(**overrides):
    fields = dict(
        project_id="project-1", observation_id="observation-1",
        object_ref="asset-revision-1", object_revision_sha256=H1,
        asset_record_sha256=H2, retention_class=RetentionClass.STANDARD,
        observation_state=ObservationState.PRESENT, observed_at=T1,
        last_used_at=T0, storage_bytes=4096, active_reference_count=0,
        pending_job_reference_count=0, legal_hold_state=HoldState.CLEAR,
        privacy_hold_state=HoldState.CLEAR,
        inventory_profile_ref="storage-inventory-profile-1",
        inventory_profile_sha256=H3,
    )
    fields.update(overrides)
    return compile_storage_observation(**fields)


def decision(*, observed=None, evaluated_at=T_ARCHIVE):
    return compile_storage_disposition(
        project_id="project-1", decision_id="decision-1", policy=policy(),
        observation=observed or observation(), evaluated_at=evaluated_at,
    )


def authorization(decision_record, observed=None, **overrides):
    observed = observed or observation()
    fields = dict(
        contract_state=ContractState.BOUND_VERIFIED,
        authorization_id="owner-authorization-1", authorization_revision=1,
        authorization_sha256=H1, authority_kind=AuthorityKind.OWNER_HUMAN_GATE,
        project_id="project-1", object_ref=observed.object_ref,
        object_revision_sha256=observed.object_revision_sha256,
        decision_sha256=decision_record.decision_sha256,
        effect=decision_record.proposed_effect, issued_at=T_ARCHIVE,
        expires_at=T_EXPIRES, one_shot=True,
        evidence_ref="owner-gate-evidence-1", evidence_sha256=H2,
    )
    fields.update(overrides)
    return StorageEffectAuthorizationBinding(**fields)


def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def assert_schema(record: dict) -> None:
    validator().validate(record)


def test_schema_mirror_and_all_canonical_records_validate() -> None:
    assert SCHEMA_PATH.read_bytes() == MIRROR_PATH.read_bytes()
    p = policy()
    o = observation()
    d = decision(observed=o)
    a = authorization(d, o)
    r = StorageEffectReceiptBinding(
        contract_state=ContractState.BOUND_VERIFIED,
        receipt_ref="canonical-effect-receipt-1", receipt_sha256=H2,
        project_id="project-1", object_ref=o.object_ref,
        object_revision_sha256=o.object_revision_sha256,
        decision_sha256=d.decision_sha256, authorization_sha256=H1,
        effect=StorageEffect.ARCHIVE, result=EffectResult.VERIFIED_ARCHIVED,
        observed_at=T_DELETE, before_observation_sha256=o.observation_sha256,
        after_observation_sha256=H3, reason_codes=["AUTHORITATIVE_READ_BACK_VERIFIED"],
    )
    for record in (p.to_dict(), o.to_dict(), d.to_dict(), a.to_dict(), r.to_dict()):
        assert_schema(record)
    assert_schema(public_storage_projection(d))
    assert_schema(public_storage_projection(r))


def test_policy_is_deterministic_append_only_and_hash_verified() -> None:
    first = policy()
    assert first.to_dict() == policy().to_dict()
    verify_storage_record_hash(first.to_dict())
    second = policy(revision=2, parent_revision_sha256=first.policy_revision_sha256)
    assert second.parent_revision_sha256 == first.policy_revision_sha256
    with pytest.raises(ValueError, match="revision 1"):
        policy(parent_revision_sha256=H1)
    with pytest.raises(ValueError, match="requires a parent"):
        policy(revision=2)
    with pytest.raises(ValueError, match="canonical order"):
        policy(rules=tuple(reversed(rules())))
    with pytest.raises(ValueError, match="greater"):
        RetentionRule(RetentionClass.STANDARD, 10, 10)
    with pytest.raises(ValueError, match="must be null"):
        RetentionRule(RetentionClass.LEGAL_HOLD, 1, 2)


@pytest.mark.parametrize("field", ["object_ref", "inventory_profile_ref"])
def test_observation_rejects_private_or_path_like_coordinates(field: str) -> None:
    with pytest.raises(ValueError, match="body-free"):
        observation(**{field: "C:\\private\\voice.wav"})
    with pytest.raises(ValueError, match="body-free"):
        observation(**{field: "../private-key"})


def test_unknown_observation_never_invents_zero_and_schema_matches() -> None:
    unknown = observation(
        observation_state=ObservationState.UNKNOWN, last_used_at=None,
        storage_bytes=None, active_reference_count=None,
        pending_job_reference_count=None, legal_hold_state=HoldState.UNKNOWN,
        privacy_hold_state=HoldState.UNKNOWN,
    )
    assert unknown.storage_bytes is None
    assert_schema(unknown.to_dict())
    with pytest.raises(ValueError, match="must not invent"):
        observation(
            observation_state=ObservationState.UNKNOWN, last_used_at=None,
            storage_bytes=0, active_reference_count=None,
            pending_job_reference_count=None, legal_hold_state=HoldState.UNKNOWN,
            privacy_hold_state=HoldState.UNKNOWN,
        )


def test_policy_decisions_keep_archive_delete_absent_hold_and_unknown() -> None:
    active = decision(observed=observation(active_reference_count=1))
    assert (active.decision, active.proposed_effect) == (LifecycleDecision.KEEP, None)
    archive = decision()
    assert (archive.decision, archive.proposed_effect) == (LifecycleDecision.ARCHIVE_PROPOSED, StorageEffect.ARCHIVE)
    delete = decision(evaluated_at=T_DELETE)
    assert (delete.decision, delete.proposed_effect) == (LifecycleDecision.DELETE_PROPOSED, StorageEffect.DELETE)
    held = decision(observed=observation(privacy_hold_state=HoldState.ACTIVE))
    assert held.decision is LifecycleDecision.BLOCKED
    absent = decision(observed=observation(observation_state=ObservationState.ABSENT, storage_bytes=0))
    assert absent.decision is LifecycleDecision.NO_ACTION_ALREADY_ABSENT
    unknown_observation = observation(
        observation_state=ObservationState.UNKNOWN, last_used_at=None,
        storage_bytes=None, active_reference_count=None,
        pending_job_reference_count=None, legal_hold_state=HoldState.UNKNOWN,
        privacy_hold_state=HoldState.UNKNOWN,
    )
    unknown = decision(observed=unknown_observation)
    assert unknown.decision is LifecycleDecision.UNKNOWN
    stale = compile_storage_disposition(
        project_id="project-1", decision_id="stale-decision", policy=policy(max_observation_age_seconds=60),
        observation=observation(), evaluated_at=T_ARCHIVE,
    )
    assert stale.decision is LifecycleDecision.UNKNOWN


def test_unresolved_authority_is_null_complete_and_fail_closed() -> None:
    unresolved = StorageEffectAuthorizationBinding(
        contract_state=ContractState.CANONICAL_REF_NOT_PROVIDED,
        authorization_id=None, authorization_revision=None, authorization_sha256=None,
        authority_kind=None, project_id=None, object_ref=None,
        object_revision_sha256=None, decision_sha256=None, effect=None,
        issued_at=None, expires_at=None, one_shot=None,
        evidence_ref=None, evidence_sha256=None,
    )
    d = decision()
    assert_schema(unresolved.to_dict())
    assert classify_effect_gate(
        policy=policy(), observation=observation(), decision=d, authorization=unresolved,
        evaluated_at=T_DELETE,
    ) is EffectGateDecision.UNKNOWN
    with pytest.raises(ValueError, match="must not invent"):
        replace(unresolved, authorization_id="forged-true")


def test_effect_gate_requires_exact_current_one_shot_owner_binding() -> None:
    o = observation()
    d = decision(observed=o)
    a = authorization(d, o)
    assert classify_effect_gate(
        policy=policy(), observation=o, decision=d, authorization=a,
        evaluated_at=T_DELETE,
    ) is EffectGateDecision.READY_FOR_EXTERNAL_EFFECT
    assert classify_effect_gate(
        policy=policy(), observation=o, decision=d, authorization=authorization(d, o, object_revision_sha256=H3),
        evaluated_at=T_DELETE,
    ) is EffectGateDecision.BLOCKED
    assert classify_effect_gate(
        policy=policy(), observation=o, decision=d,
        authorization=authorization(d, o, issued_at="2026-08-17T00:50:00Z"),
        evaluated_at=T_DELETE,
    ) is EffectGateDecision.BLOCKED
    assert classify_effect_gate(
        policy=policy(), observation=o, decision=d,
        authorization=authorization(d, o, expires_at=T_DELETE),
        evaluated_at=T_DELETE,
    ) is EffectGateDecision.BLOCKED
    changed_policy = policy(revision=2, parent_revision_sha256=policy().policy_revision_sha256)
    assert classify_effect_gate(
        policy=changed_policy, observation=o, decision=d, authorization=a,
        evaluated_at=T_DELETE,
    ) is EffectGateDecision.BLOCKED
    tampered = replace(d, decision_sha256=H3)
    assert classify_effect_gate(
        policy=policy(), observation=o, decision=tampered,
        authorization=authorization(d, o), evaluated_at=T_DELETE,
    ) is EffectGateDecision.BLOCKED


def test_authorization_rejects_bad_window_replay_and_forgeable_boolean_shape() -> None:
    d = decision()
    with pytest.raises(ValueError, match="expiry"):
        authorization(d, issued_at=T_EXPIRES, expires_at=T_DELETE)
    with pytest.raises(ValueError, match="one-shot"):
        authorization(d, one_shot=False)
    forged = authorization(d).to_dict()
    forged["execution_authorized"] = True
    with pytest.raises(Exception):
        assert_schema(forged)


def test_external_effect_receipt_binding_separates_verified_unknown_and_no_retry() -> None:
    o = observation()
    d = decision(observed=o)
    verified = StorageEffectReceiptBinding(
        contract_state=ContractState.BOUND_VERIFIED,
        receipt_ref="canonical-receipt-verified", receipt_sha256=H2,
        project_id="project-1",
        object_ref=o.object_ref, object_revision_sha256=o.object_revision_sha256,
        decision_sha256=d.decision_sha256, authorization_sha256=H1,
        effect=StorageEffect.ARCHIVE, result=EffectResult.VERIFIED_ARCHIVED,
        observed_at=T_DELETE, before_observation_sha256=o.observation_sha256,
        after_observation_sha256=H3, reason_codes=["AUTHORITATIVE_READ_BACK_VERIFIED"],
    )
    assert verified.to_dict()["automatic_retry_authorized"] is False
    with pytest.raises(ValueError, match="requires after observation"):
        StorageEffectReceiptBinding(
            contract_state=ContractState.BOUND_VERIFIED,
            receipt_ref="canonical-receipt-no-readback", receipt_sha256=H2,
            project_id="project-1",
            object_ref=o.object_ref, object_revision_sha256=o.object_revision_sha256,
            decision_sha256=d.decision_sha256, authorization_sha256=H1,
            effect=StorageEffect.ARCHIVE, result=EffectResult.VERIFIED_ARCHIVED,
            observed_at=T_DELETE, before_observation_sha256=o.observation_sha256,
            after_observation_sha256=None, reason_codes=[],
        )
    unknown = StorageEffectReceiptBinding(
        contract_state=ContractState.BOUND_VERIFIED,
        receipt_ref="canonical-receipt-unknown", receipt_sha256=H2,
        project_id="project-1",
        object_ref=o.object_ref, object_revision_sha256=o.object_revision_sha256,
        decision_sha256=d.decision_sha256, authorization_sha256=H1,
        effect=StorageEffect.DELETE, result=EffectResult.UNKNOWN,
        observed_at=T_DELETE, before_observation_sha256=o.observation_sha256,
        after_observation_sha256=None, reason_codes=["EXTERNAL_STATE_UNKNOWN"],
    )
    assert unknown.result is EffectResult.UNKNOWN
    with pytest.raises(ValueError, match="EXTERNAL_STATE_UNKNOWN"):
        StorageEffectReceiptBinding(
            contract_state=ContractState.BOUND_VERIFIED,
            receipt_ref="canonical-receipt-bad-unknown", receipt_sha256=H2,
            project_id="project-1",
            object_ref=o.object_ref, object_revision_sha256=o.object_revision_sha256,
            decision_sha256=d.decision_sha256, authorization_sha256=H1,
            effect=StorageEffect.DELETE, result=EffectResult.UNKNOWN,
            observed_at=T_DELETE, before_observation_sha256=o.observation_sha256,
            after_observation_sha256=None, reason_codes=["TIMEOUT"],
        )
    unresolved = StorageEffectReceiptBinding(
        contract_state=ContractState.UNKNOWN, receipt_ref=None,
        receipt_sha256=None, project_id=None, object_ref=None,
        object_revision_sha256=None, decision_sha256=None,
        authorization_sha256=None, effect=None, result=None,
        observed_at=None, before_observation_sha256=None,
        after_observation_sha256=None, reason_codes=(),
    )
    assert_schema(unresolved.to_dict())
    assert public_storage_projection(unresolved)["result"] is None


def test_hash_tamper_schema_cross_fields_and_extra_properties_are_rejected() -> None:
    record = decision().to_dict()
    tampered = copy.deepcopy(record)
    tampered["reason_codes"] = ["TAMPERED"]
    with pytest.raises(ValueError, match="mismatch"):
        verify_storage_record_hash(tampered)
    invalid = copy.deepcopy(record)
    invalid["proposed_effect"] = "DELETE"
    with pytest.raises(Exception):
        assert_schema(invalid)
    invalid = copy.deepcopy(record)
    invalid["raw_path"] = "C:/private/audio.wav"
    with pytest.raises(Exception):
        assert_schema(invalid)


def test_public_projection_contains_no_private_identity_or_digest() -> None:
    public = public_storage_projection(decision())
    encoded = json.dumps(public, sort_keys=True)
    for forbidden in ("object_ref", "asset_record", "observation_sha", "policy_revision", "path", "credential"):
        assert forbidden not in encoded.casefold()
    assert public["private_coordinate_suppressed"] is True
    assert public["effect_started"] is False


def test_module_has_no_filesystem_process_network_or_effect_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imported.intersection({"os", "pathlib", "subprocess", "socket", "requests", "shutil"})
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not calls.intersection({"open", "remove", "unlink", "rmdir", "rename", "replace"})
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "execution_authorized" not in source
    assert "compile_effect_receipt" not in source
    assert "automatic_delete_authorized\": False" in source
    assert "effect_performed_by_module\": False" in source
