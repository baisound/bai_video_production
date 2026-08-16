from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.integrated_dashboard_operations import (
    EFFECT_SURFACE,
    ContractState,
    DashboardAlertClassificationReceipt,
    DashboardEvidenceReadModel,
    DashboardExecutionReceiptBinding,
    DashboardIncidentReadModel,
    DashboardJobReadModel,
    DashboardOperationProposalRevision,
    DashboardProjectionPolicyRevision,
    DashboardQueryIntent,
    DashboardSnapshotState,
    DashboardSourceBinding,
    HumanOperationConfirmationBinding,
    IntegratedDashboardSnapshotRevision,
    build_snapshot,
    classify_alert,
    operation_admission_report,
    public_projection,
    validate_record,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "integrated-dashboard-operations.schema.json"
MIRROR_PATH = ROOT / "src" / "ai_video_production" / "schema_resources" / "integrated-dashboard-operations.schema.json"
MODULE_PATH = ROOT / "src" / "ai_video_production" / "integrated_dashboard_operations.py"
H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
H3 = "sha256:" + "3" * 64
T0 = "2026-08-17T00:00:00Z"
T1 = "2026-08-17T00:05:00Z"
T2 = "2026-08-17T01:00:00Z"


def policy(**overrides):
    fields = dict(
        policy_id="dashboard-policy-1", revision=1, parent_record_sha256=None,
        max_source_age_seconds=600, max_page_size=100, max_sources=32,
        max_items=128, max_alerts=32, max_incidents=32,
        authority_ref="task021-policy-owner", authority_sha256=H1,
        effective_at=T0, expires_at=None,
    )
    fields.update(overrides)
    return DashboardProjectionPolicyRevision.create(**fields)


def source(*, kind="DURABLE_JOB", freshness="CURRENT", validity="CURRENT", **overrides):
    fields = dict(
        source_id=f"source-{kind.lower()}", source_kind=kind,
        contract_state="BOUND_VERIFIED", source_ref=f"canonical-{kind.lower()}-revision",
        source_sha256=H2, source_revision=1, observed_at=T0,
        freshness_state=freshness, validity_state=validity,
        public_projection_only=kind == "PRIVACY_PUBLIC", body_included=False,
        private_path_included=False,
    )
    fields.update(overrides)
    return DashboardSourceBinding.create(**fields)


def query(**overrides):
    fields = dict(
        query_id="query-1", project_id="project-1",
        source_kinds=["DURABLE_JOB", "PRIVACY_PUBLIC"],
        state_filters=["ACTIVE", "FAILED"], page_size=100,
        cursor_sha256=None, sort_order="UPDATED_AT_ASC", body_included=False,
    )
    fields.update(overrides)
    return DashboardQueryIntent.create(**fields)


def job(*, binding=None, state="SUCCEEDED", freshness="CURRENT", **overrides):
    binding = binding or source()
    fields = dict(
        view_id="job-view-1", source_binding_sha256=binding.record_sha256,
        job_sha256=H1, operation_identity="operation-1", job_state=state,
        state_version=1, attempt=0, updated_at=T0, freshness_state=freshness,
        reason_codes=[], effect_started_by_dashboard=False,
    )
    fields.update(overrides)
    return DashboardJobReadModel.create(**fields)


def evidence(*, binding=None, result="PASS", freshness="CURRENT", **overrides):
    binding = binding or source(kind="EVIDENCE")
    fields = dict(
        view_id="evidence-view-1", source_binding_sha256=binding.record_sha256,
        evidence_record_type="ResourceAdmissionDecisionReceipt",
        evidence_sha256=H2, result_state=result, observed_at=T0,
        freshness_state=freshness, reason_codes=[], body_included=False,
    )
    fields.update(overrides)
    return DashboardEvidenceReadModel.create(**fields)


def incident(*, binding=None, state="ACTIVE", severity="HIGH", freshness="CURRENT", **overrides):
    binding = binding or source(kind="AUDIT")
    fields = dict(
        view_id="incident-view-1", source_binding_sha256=binding.record_sha256,
        incident_id="incident-1", incident_state=state, severity=severity,
        observed_at=T0, resolved_receipt_sha256=H3 if state == "RESOLVED_PROVEN" else None,
        freshness_state=freshness, reason_codes=[], absence_assumed_healthy=False,
    )
    fields.update(overrides)
    return DashboardIncidentReadModel.create(**fields)


def proposal(snapshot_hash=H1, **overrides):
    fields = dict(
        proposal_id="proposal-1", revision=1, parent_record_sha256=None,
        snapshot_sha256=snapshot_hash, operation_kind="REQUEST_PAUSE",
        target_source_sha256=H2, expected_target_state_version=1,
        precondition_hashes=[H1, H2], proposal_state="PROPOSED",
        reason_codes=[], created_at=T0, expires_at=T2,
        proposal_only=True, execution_started=False,
    )
    fields.update(overrides)
    return DashboardOperationProposalRevision.create(**fields)


def confirmation(p, **overrides):
    fields = dict(
        contract_state="BOUND_VERIFIED", confirmation_id="confirmation-1",
        confirmation_revision=1, confirmation_sha256=H3,
        proposal_sha256=p.record_sha256, snapshot_sha256=p.to_dict()["snapshot_sha256"],
        target_source_sha256=p.to_dict()["target_source_sha256"],
        operation_kind=p.to_dict()["operation_kind"], reviewer_kind="HUMAN",
        decision="APPROVE", decided_at=T0, expires_at=T2,
        one_shot=True, consumed=False, evidence_ref="owner-gate-evidence",
        evidence_sha256=H1,
    )
    fields.update(overrides)
    return HumanOperationConfirmationBinding.create(**fields)


def execution(p, c, **overrides):
    fields = dict(
        contract_state="BOUND_VERIFIED", receipt_id="receipt-1",
        receipt_ref="canonical-external-receipt", receipt_sha256=H1,
        proposal_sha256=p.record_sha256, confirmation_sha256=c.record_sha256,
        operation_identity="external-operation-1", external_state="ACCEPTED",
        observed_at=T1, canonical_persistence_verified=True,
        effect_started_by_dashboard=False,
    )
    fields.update(overrides)
    return DashboardExecutionReceiptBinding.create(**fields)


def snapshot_record(**overrides):
    s = source()
    fields = dict(
        snapshot_id="snapshot-1", revision=1, parent_record_sha256=None,
        project_id="project-1", policy_sha256=policy().record_sha256,
        query_sha256=query().record_sha256, source_binding_hashes=[s.record_sha256],
        job_view_hashes=[], evidence_view_hashes=[], incident_view_hashes=[],
        alert_hashes=[], coverage_state="COMPLETE",
        snapshot_state="NO_ACTIVE_INCIDENT_PROVEN", source_watermark_sha256=H3,
        generated_at=T1, body_included=False, private_detail_included=False,
        effect_started_by_dashboard=False,
    )
    fields.update(overrides)
    return IntegratedDashboardSnapshotRevision.create(**fields)


def roots():
    p = policy()
    s = source()
    j = job(binding=s)
    ev_source = source(kind="EVIDENCE")
    ev = evidence(binding=ev_source)
    inc_source = source(kind="AUDIT")
    inc = incident(binding=inc_source)
    alert = classify_alert(alert_id="alert-1", policy=p, subject=inc, incident=inc, classified_at=T1)
    snap = build_snapshot(
        snapshot_id="snapshot-1", revision=1, parent_record_sha256=None,
        project_id="project-1", policy=p,
        query=query(source_kinds=["AUDIT", "DURABLE_JOB", "EVIDENCE"]),
        sources=[s, ev_source, inc_source], jobs=[j], evidence=[ev], incidents=[inc],
        alerts=[alert], coverage_state="COMPLETE", source_watermark_sha256=H3,
        generated_at=T1,
    )
    op = proposal(snap.record_sha256)
    human = confirmation(op)
    receipt = execution(op, human)
    return [p, s, query(), j, ev, inc, alert, snap, op, human, receipt]


def test_schema_mirror_is_byte_exact_and_accepts_all_eleven_roots():
    assert SCHEMA_PATH.read_bytes() == MIRROR_PATH.read_bytes()
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    records = roots()
    assert len(records) == 11
    for record in records:
        validator.validate(record.to_dict())
        assert validate_record(record.to_dict()).record_sha256 == record.record_sha256


def test_hash_is_deterministic_and_tamper_or_unknown_field_fails_closed():
    first = policy()
    assert first.record_sha256 == policy().record_sha256
    tampered = first.to_dict()
    tampered["max_items"] = 129
    with pytest.raises(ValueError, match="record_sha256 mismatch"):
        validate_record(tampered)
    extra = first.to_dict()
    extra["execution_authorized"] = True
    with pytest.raises(ValueError, match="incomplete or unknown"):
        validate_record(extra)


def test_revision_parent_and_time_order_are_strict():
    with pytest.raises(ValueError, match="parent/revision"):
        policy(revision=2, parent_record_sha256=None)
    with pytest.raises(ValueError, match="follow"):
        policy(effective_at=T2, expires_at=T1)


def test_unresolved_source_cannot_invent_truth_and_privacy_must_be_public():
    with pytest.raises(ValueError, match="invents canonical"):
        source(
            contract_state="CANONICAL_REF_NOT_PROVIDED", source_ref="invented",
            source_sha256=None, source_revision=None, observed_at=None,
            freshness_state="UNKNOWN", validity_state="UNKNOWN",
        )
    with pytest.raises(ValueError, match="public projection"):
        source(kind="PRIVACY_PUBLIC", public_projection_only=False)


@pytest.mark.parametrize("bad", ["C:/private/audio.wav", "../secret", "access-token-ref"])
def test_path_and_credential_like_identifiers_are_rejected(bad):
    with pytest.raises(ValueError, match="invalid|body-free"):
        source(source_ref=bad)


def test_query_caps_duplicates_and_canonical_order_are_enforced():
    with pytest.raises(ValueError, match="outside its cap"):
        query(page_size=201)
    with pytest.raises(ValueError, match="unique"):
        query(state_filters=["ACTIVE", "ACTIVE"])
    with pytest.raises(ValueError, match="canonical sorted order"):
        query(source_kinds=["PRIVACY_PUBLIC", "DURABLE_JOB"])


def test_active_and_acknowledged_incident_remain_action_required():
    p = policy()
    s = source(kind="AUDIT")
    inc = incident(binding=s)
    ack = classify_alert(
        alert_id="alert-ack", policy=p, subject=inc, incident=inc,
        classified_at=T1, acknowledgement_receipt_sha256=H1,
    )
    assert ack.to_dict()["lifecycle"] == "ACKNOWLEDGED"
    snap = build_snapshot(
        snapshot_id="snap-active", revision=1, parent_record_sha256=None,
        project_id="project-1", policy=p,
        query=query(source_kinds=["AUDIT"], state_filters=[]), sources=[s],
        jobs=[], evidence=[], incidents=[inc], alerts=[ack], coverage_state="COMPLETE",
        source_watermark_sha256=H2, generated_at=T1,
    )
    assert snap.to_dict()["snapshot_state"] == "ACTION_REQUIRED"


def test_empty_incident_set_is_only_healthy_with_complete_current_coverage():
    p = policy()
    s = source()
    complete = build_snapshot(
        snapshot_id="snap-complete", revision=1, parent_record_sha256=None,
        project_id="project-1", policy=p, query=query(source_kinds=["DURABLE_JOB"], state_filters=[]),
        sources=[s], jobs=[job(binding=s)], evidence=[], incidents=[], alerts=[],
        coverage_state="COMPLETE", source_watermark_sha256=H2, generated_at=T1,
    )
    assert complete.to_dict()["snapshot_state"] == "NO_ACTIVE_INCIDENT_PROVEN"
    partial = build_snapshot(
        snapshot_id="snap-partial", revision=1, parent_record_sha256=None,
        project_id="project-1", policy=p, query=query(source_kinds=["DURABLE_JOB"], state_filters=[]),
        sources=[s], jobs=[job(binding=s)], evidence=[], incidents=[], alerts=[],
        coverage_state="PARTIAL", source_watermark_sha256=H2, generated_at=T1,
    )
    assert partial.to_dict()["snapshot_state"] == "UNKNOWN"


@pytest.mark.parametrize(
    ("source_kwargs", "expected"),
    [({"freshness": "UNKNOWN"}, "UNKNOWN"), ({"freshness": "STALE"}, "STALE"), ({"validity": "INVALIDATED"}, "STALE")],
)
def test_unknown_stale_and_invalidated_sources_fail_closed(source_kwargs, expected):
    s = source(**source_kwargs)
    snap = build_snapshot(
        snapshot_id="snap-state", revision=1, parent_record_sha256=None,
        project_id="project-1", policy=policy(),
        query=query(source_kinds=["DURABLE_JOB"], state_filters=[]), sources=[s],
        jobs=[], evidence=[], incidents=[], alerts=[], coverage_state="COMPLETE",
        source_watermark_sha256=H2, generated_at=T1,
    )
    assert snap.to_dict()["snapshot_state"] == expected


def test_observation_age_is_evaluated_against_policy_not_trusted_as_current():
    s = source(observed_at=T0)
    snap = build_snapshot(
        snapshot_id="snap-aged", revision=1, parent_record_sha256=None,
        project_id="project-1", policy=policy(max_source_age_seconds=60),
        query=query(source_kinds=["DURABLE_JOB"], state_filters=[]), sources=[s],
        jobs=[], evidence=[], incidents=[], alerts=[], coverage_state="COMPLETE",
        source_watermark_sha256=H2, generated_at=T1,
    )
    assert snap.to_dict()["snapshot_state"] == "STALE"


@pytest.mark.parametrize(("job_state", "result", "expected"), [
    ("FAILED", "PASS", "ACTION_REQUIRED"),
    ("RUNNING", "PASS", "DEGRADED"),
    ("SUCCEEDED", "UNKNOWN", "UNKNOWN"),
])
def test_job_and_evidence_states_classify_without_effect(job_state, result, expected):
    job_source = source()
    ev_source = source(kind="EVIDENCE")
    snap = build_snapshot(
        snapshot_id="snap-work", revision=1, parent_record_sha256=None,
        project_id="project-1", policy=policy(),
        query=query(source_kinds=["DURABLE_JOB", "EVIDENCE"]),
        sources=[job_source, ev_source],
        jobs=[job(binding=job_source, state=job_state)], evidence=[evidence(binding=ev_source, result=result)],
        incidents=[], alerts=[], coverage_state="COMPLETE", source_watermark_sha256=H2,
        generated_at=T1,
    )
    assert snap.to_dict()["snapshot_state"] == expected


def test_incident_resolution_and_alert_ack_require_exact_receipts():
    with pytest.raises(ValueError, match="exact receipt"):
        incident(state="ACTIVE", resolved_receipt_sha256=H1)
    inc = incident()
    alert = classify_alert(alert_id="alert-open", policy=policy(), subject=inc, incident=inc, classified_at=T1)
    bad = alert.to_dict()
    bad["lifecycle"] = "ACKNOWLEDGED"
    bad["record_sha256"] = H1
    with pytest.raises(ValueError, match="exact receipt"):
        DashboardAlertClassificationReceipt.from_dict(bad)


def test_resolved_incident_history_can_coexist_with_proven_no_active_state():
    p = policy()
    s = source(kind="AUDIT")
    resolved = incident(binding=s, state="RESOLVED_PROVEN", severity="INFO")
    alert = classify_alert(
        alert_id="alert-resolved", policy=p, subject=resolved, incident=resolved,
        classified_at=T1,
    )
    snap = build_snapshot(
        snapshot_id="snap-resolved", revision=1, parent_record_sha256=None,
        project_id="project-1", policy=p,
        query=query(source_kinds=["AUDIT"], state_filters=[]), sources=[s],
        jobs=[], evidence=[], incidents=[resolved], alerts=[alert],
        coverage_state="COMPLETE", source_watermark_sha256=H2, generated_at=T1,
    )
    assert snap.to_dict()["snapshot_state"] == "NO_ACTIVE_INCIDENT_PROVEN"


def test_snapshot_rejects_cross_source_read_model_and_noncurrent_policy():
    selected = source()
    foreign = source(source_id="source-foreign", source_sha256=H3)
    with pytest.raises(ValueError, match="exact selected source"):
        build_snapshot(
            snapshot_id="snap-cross-source", revision=1, parent_record_sha256=None,
            project_id="project-1", policy=policy(),
            query=query(source_kinds=["DURABLE_JOB"], state_filters=[]),
            sources=[selected], jobs=[job(binding=foreign)], evidence=[], incidents=[], alerts=[],
            coverage_state="COMPLETE", source_watermark_sha256=H2, generated_at=T1,
        )
    with pytest.raises(ValueError, match="not current"):
        build_snapshot(
            snapshot_id="snap-expired-policy", revision=1, parent_record_sha256=None,
            project_id="project-1", policy=policy(expires_at=T1),
            query=query(source_kinds=["DURABLE_JOB"], state_filters=[]),
            sources=[selected], jobs=[], evidence=[], incidents=[], alerts=[],
            coverage_state="COMPLETE", source_watermark_sha256=H2, generated_at=T1,
        )


def test_proposal_is_no_effect_and_preconditions_use_canonical_order():
    p = proposal()
    assert p.to_dict()["proposal_only"] is True
    assert p.to_dict()["execution_started"] is False
    with pytest.raises(ValueError, match="canonical sorted order"):
        proposal(precondition_hashes=[H2, H1])
    with pytest.raises(ValueError, match="proposal-only"):
        proposal(execution_started=True)


def test_unresolved_human_binding_is_all_null_and_cannot_be_ai_forged():
    unresolved = HumanOperationConfirmationBinding.create(
        contract_state="CANONICAL_REF_NOT_PROVIDED", confirmation_id=None,
        confirmation_revision=None, confirmation_sha256=None, proposal_sha256=None,
        snapshot_sha256=None, target_source_sha256=None, operation_kind=None,
        reviewer_kind=None, decision=None, decided_at=None, expires_at=None,
        one_shot=None, consumed=None, evidence_ref=None, evidence_sha256=None,
    )
    assert unresolved.to_dict()["decision"] is None
    p = proposal()
    with pytest.raises(ValueError, match="reviewer_kind"):
        confirmation(p, reviewer_kind="AI")


def test_operation_admission_is_metadata_only_and_requires_exact_current_human_gate():
    p = proposal()
    blocked = operation_admission_report(proposal=p, confirmation=None, execution_receipt=None, evaluated_at=T1)
    assert blocked["gate_decision"] == "BLOCKED"
    current = confirmation(p)
    candidate = operation_admission_report(proposal=p, confirmation=current, execution_receipt=None, evaluated_at=T1)
    assert candidate["gate_decision"] == "READY_FOR_EXTERNAL_HUMAN_GATE"
    assert all(candidate[field] is False for field in (
        "dispatch_started", "process_started", "app_operation_started", "alert_sent", "production_effect_started"
    ))
    expired = confirmation(p, expires_at=T1)
    assert operation_admission_report(
        proposal=p, confirmation=expired, execution_receipt=None, evaluated_at=T1,
    )["gate_decision"] == "BLOCKED"


def test_external_unknown_is_not_replayed_and_accepted_requires_persistence():
    p = proposal()
    c = confirmation(p)
    unknown = execution(p, c, external_state="UNKNOWN", canonical_persistence_verified=False)
    report = operation_admission_report(proposal=p, confirmation=c, execution_receipt=unknown, evaluated_at=T1)
    assert report["gate_decision"] == "RESULT_RECORDED"
    assert "EXTERNAL_RESULT_UNKNOWN_NO_REPLAY" in report["reason_codes"]
    with pytest.raises(ValueError, match="persistence"):
        execution(p, c, canonical_persistence_verified=False)


def test_public_projection_suppresses_source_coordinates_and_private_details():
    result = public_projection(source(kind="PRIVACY_PUBLIC"))
    assert result["record_type"] == "DashboardSourceBinding"
    assert result["body_included"] is False
    assert "source_ref" not in result
    assert "source_sha256" not in result
    assert "source_revision" not in result
    assert "observed_at" not in result


def test_static_surface_has_no_io_runtime_or_effect_authority():
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imports.isdisjoint({"os", "pathlib", "subprocess", "socket", "requests", "urllib", "http"})
    assert set(EFFECT_SURFACE.values()) == {False}
    source_text = MODULE_PATH.read_text(encoding="utf-8")
    assert "execution_authorized" not in source_text
    assert "admissible_for_external_dispatch" not in source_text


def test_schema_rejects_unknown_fields_and_effect_flags():
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    item = job().to_dict()
    item["effect_started_by_dashboard"] = True
    assert list(validator.iter_errors(item))
    item = job().to_dict()
    item["private_path"] = "C:/secret"
    assert list(validator.iter_errors(item))


def test_snapshot_hash_arrays_cannot_be_reordered_or_duplicated():
    snap = snapshot_record(source_binding_hashes=[H1, H2])
    assert snap.to_dict()["source_binding_hashes"] == [H1, H2]
    with pytest.raises(ValueError, match="canonical sorted order"):
        snapshot_record(source_binding_hashes=[H2, H1])
    with pytest.raises(ValueError, match="unique"):
        snapshot_record(source_binding_hashes=[H1, H1])


def test_existing_production_dashboard_contract_remains_importable():
    from ai_video_production import production_dashboard

    assert callable(production_dashboard.ProductionDashboardProjection)
    assert not hasattr(production_dashboard, "IntegratedDashboardSnapshotRevision")
