from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production import reaper_audio_finishing as raf


H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
H3 = "sha256:" + "3" * 64
H4 = "sha256:" + "4" * 64
NOW = "2026-08-17T01:00:00Z"


def policy(**overrides):
    fields = dict(
        policy_id="policy:task035:r0", revision=1, parent_record_sha256=None,
        required_sample_rate_hz=48_000, max_tracks=64, max_routes=128,
        max_render_targets=8, allow_human_owned_mutation=False,
        official_policy_ref="task035:policy:r0", official_policy_sha256=H1,
        effective_at="2026-08-17T00:00:00Z", expires_at=None,
    )
    fields.update(overrides)
    return raf.DawFinishingPolicyRevision.create(**fields)


def source(**overrides):
    fields = dict(
        source_id="source:asset:1", source_kind="ASSET_REVISION",
        contract_state="BOUND_VERIFIED", canonical_ref="asset:1",
        canonical_sha256=H1, canonical_revision=1, rights_state="PASS",
        observed_at=NOW, body_included=False, absolute_path_included=False,
    )
    fields.update(overrides)
    return raf.DawSourceBinding.create(**fields)


def capability(**overrides):
    fields = dict(
        report_id="capability:reaper:7.78", reaper_version="7.78",
        platform="WINDOWS_X64", executable_sha256=H2,
        reascript_api_state="SUPPORTED", project_read_state="SUPPORTED",
        project_write_state="SUPPORTED", undo_state="SUPPORTED",
        render_mix_state="SUPPORTED", render_stems_state="PROBE_REQUIRED",
        plugin_inventory_state="UNKNOWN", plugin_inventory_sha256=None,
        license_state="VERIFIED", probed_at=NOW, probe_profile_sha256=H3,
        private_path_included=False, license_data_included=False,
    )
    fields.update(overrides)
    return raf.DawCapabilityReport.create(**fields)


def plan(source_hashes, capability_hash, **overrides):
    fields = dict(
        session_plan_id="session-plan:1", production_job_id="job:1", revision=1,
        parent_record_sha256=None, project_id="project:1",
        source_binding_hashes=list(source_hashes), timeline_binding_sha256=H1,
        audio_workspace_sha256=H2, resource_admission_sha256=H3,
        capability_report_sha256=capability_hash, sample_rate_hz=48_000,
        frame_rate_numerator=30_000, frame_rate_denominator=1_001,
        channel_layout="STEREO", track_spec_hashes=[H1], route_spec_hashes=[H2],
        render_target_hashes=[H3], ownership="AUTOMATION_OWNED",
        plan_state="PREFLIGHT_READY", reason_codes=[], body_included=False,
        absolute_path_included=False, execution_started=False,
    )
    fields.update(overrides)
    return raf.DawSessionPlan.create(**fields)


def unresolved_authorization(**overrides):
    fields = dict(
        contract_state="CANONICAL_REF_NOT_PROVIDED", authorization_id=None,
        authorization_revision=None, authorization_sha256=None,
        session_plan_sha256=None, capability_report_sha256=None,
        resource_gate_sha256=None, operation=None, authority_kind=None,
        issued_at=None, expires_at=None, one_shot=None, consumed=None,
        evidence_ref=None, evidence_sha256=None,
    )
    fields.update(overrides)
    return raf.DawExecutionAuthorizationBinding.create(**fields)


def execution(**overrides):
    fields = dict(
        contract_state="BOUND_VERIFIED", receipt_ref="receipt:execution:1",
        receipt_sha256=H1, operation_identity="operation:1", operation="RENDER_MIX",
        session_plan_sha256=H2, authorization_sha256=H3,
        before_snapshot_sha256=H1, after_snapshot_sha256=H4,
        external_state="COMPLETED", started_at="2026-08-17T01:00:00Z",
        completed_at="2026-08-17T01:01:00Z", canonical_persistence_verified=True,
        effect_started_by_module=False,
    )
    fields.update(overrides)
    return raf.DawExecutionReceiptBinding.create(**fields)


def manifest(**overrides):
    fields = dict(
        manifest_id="roundtrip:1", revision=1, parent_record_sha256=None,
        project_id="project:1", session_plan_sha256=H1,
        project_snapshot_sha256=H2, execution_receipt_sha256=H3,
        rendered_asset_binding_hashes=[H1], qa_receipt_hashes=[],
        human_approval_sha256=None, resolve_placement_plan_sha256=None,
        round_trip_state="RENDER_CANDIDATE", reason_codes=[],
        untreated_source_preserved=True, asset_promotion_started=False,
        resolve_mutation_started=False, publication_started=False,
    )
    fields.update(overrides)
    return raf.AudioRoundTripManifest.create(**fields)


def test_schema_mirror_is_byte_exact_and_valid():
    root = Path(__file__).resolve().parents[1]
    public = root / "schemas" / "reaper-audio-finishing.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / public.name
    assert public.read_bytes() == mirror.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy().to_dict())


def test_all_ten_root_types_round_trip_and_hash():
    cap = capability()
    src = source()
    records = [
        policy(), src, cap, plan([src.record_sha256], cap.record_sha256),
        unresolved_authorization(),
        raf.DawProjectSnapshotBinding.create(
            contract_state="CANONICAL_REF_NOT_PROVIDED", snapshot_ref=None,
            snapshot_sha256=None, session_plan_sha256=None, project_state_sha256=None,
            reaper_version=None, ownership=None, observed_at=None,
            retained_as_evidence=None, absolute_path_included=False,
        ),
        execution(),
        raf.AudioQaReceiptBinding.create(
            contract_state="CANONICAL_REF_NOT_PROVIDED", qa_receipt_ref=None,
            qa_receipt_sha256=None, rendered_candidate_sha256=None,
            quality_policy_sha256=None, analyzer_profile_sha256=None,
            sample_rate_hz=None, channel_layout=None, duration_samples=None,
            qa_decision=None, observed_at=None, audio_analyzed_by_module=False,
        ),
        raf.HumanMixApprovalBinding.create(
            contract_state="CANONICAL_REF_NOT_PROVIDED", approval_id=None,
            approval_sha256=None, candidate_manifest_sha256=None,
            qa_receipt_sha256=None, decision=None, reviewer_kind=None,
            decided_at=None, evidence_ref=None, evidence_sha256=None,
        ),
        manifest(),
    ]
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas" / "reaper-audio-finishing.schema.json").read_text(encoding="utf-8"))
    schema_validator = Draft202012Validator(schema)
    assert {r.RECORD_TYPE for r in records} == set(raf._CLASSES)
    for record in records:
        schema_validator.validate(record.to_dict())
        assert raf.validate_record(record.to_dict()).record_sha256 == record.record_sha256


def test_hash_is_deterministic_and_tamper_is_rejected():
    first = policy()
    second = policy()
    assert first.record_sha256 == second.record_sha256
    tampered = first.to_dict()
    tampered["max_tracks"] = 32
    with pytest.raises(ValueError, match="record_sha256 mismatch"):
        raf.validate_record(tampered)


@pytest.mark.parametrize("bad", [r"C:\\private\\file.wav", "/private/file.wav", "../file.wav", "credential:abc"])
def test_private_path_and_credential_coordinates_are_rejected(bad):
    with pytest.raises(ValueError, match="boundary|invalid"):
        source(canonical_ref=bad)


def test_unresolved_source_cannot_invent_truth():
    with pytest.raises(ValueError, match="invents canonical"):
        source(contract_state="CANONICAL_REF_NOT_PROVIDED", canonical_ref="asset:1",
               canonical_sha256=None, canonical_revision=None, observed_at=None,
               rights_state="UNKNOWN")


def test_supported_plugin_inventory_requires_digest_and_unknown_rejects_digest():
    with pytest.raises(ValueError, match="inventory"):
        capability(plugin_inventory_state="SUPPORTED", plugin_inventory_sha256=None)
    with pytest.raises(ValueError, match="inventory"):
        capability(plugin_inventory_state="UNKNOWN", plugin_inventory_sha256=H1)


def test_human_owned_plan_cannot_be_automation_ready():
    cap, src = capability(), source()
    with pytest.raises(ValueError, match="Human-owned"):
        plan([src.record_sha256], cap.record_sha256, ownership="HUMAN_OWNED")


def test_raw_execution_authorized_boolean_and_unknown_fields_are_rejected():
    payload = unresolved_authorization().to_dict()
    payload["execution_authorized"] = True
    with pytest.raises(ValueError, match="fields"):
        raf.validate_record(payload)


def test_bound_authorization_must_be_owner_one_shot_unused_and_unexpired():
    with pytest.raises(ValueError, match="one-shot"):
        raf.DawExecutionAuthorizationBinding.create(
            contract_state="BOUND_VERIFIED", authorization_id="auth:1",
            authorization_revision=1, authorization_sha256=H1,
            session_plan_sha256=H2, capability_report_sha256=H3,
            resource_gate_sha256=H4, operation="RENDER_MIX",
            authority_kind="OWNER_HUMAN_GATE", issued_at=NOW,
            expires_at="2026-08-17T02:00:00Z", one_shot=False, consumed=False,
            evidence_ref="evidence:1", evidence_sha256=H1,
        )


def test_completed_execution_requires_after_snapshot_and_persistence():
    with pytest.raises(ValueError, match="after snapshot"):
        execution(after_snapshot_sha256=None)
    with pytest.raises(ValueError, match="persistence"):
        execution(canonical_persistence_verified=False)
    unknown = execution(external_state="UNKNOWN", after_snapshot_sha256=None,
                        completed_at=None, canonical_persistence_verified=False)
    assert unknown.to_dict()["external_state"] == "UNKNOWN"


def test_qa_pass_requires_48k_and_module_never_analyzes_audio():
    common = dict(
        contract_state="BOUND_VERIFIED", qa_receipt_ref="qa:1",
        qa_receipt_sha256=H1, rendered_candidate_sha256=H2,
        quality_policy_sha256=H3, analyzer_profile_sha256=H4,
        channel_layout="STEREO", duration_samples=48_000, qa_decision="PASS",
        observed_at=NOW, audio_analyzed_by_module=False,
    )
    with pytest.raises(ValueError, match="48000"):
        raf.AudioQaReceiptBinding.create(sample_rate_hz=44_100, **common)
    with pytest.raises(ValueError, match="cannot analyze"):
        raf.AudioQaReceiptBinding.create(sample_rate_hz=48_000,
                                         **{**common, "audio_analyzed_by_module": True})


def test_approval_dag_binds_prior_candidate_not_final_manifest():
    candidate = manifest()
    approval = raf.HumanMixApprovalBinding.create(
        contract_state="BOUND_VERIFIED", approval_id="approval:1",
        approval_sha256=H1, candidate_manifest_sha256=candidate.record_sha256,
        qa_receipt_sha256=H2, decision="APPROVE", reviewer_kind="OWNER",
        decided_at=NOW, evidence_ref="evidence:approval:1", evidence_sha256=H3,
    )
    approved = manifest(
        revision=2, parent_record_sha256=candidate.record_sha256,
        qa_receipt_hashes=[H2], human_approval_sha256=approval.record_sha256,
        round_trip_state="HUMAN_APPROVED",
    )
    assert approved.to_dict()["parent_record_sha256"] == candidate.record_sha256
    assert approval.to_dict()["candidate_manifest_sha256"] == candidate.record_sha256


def test_manifest_state_guards_prevent_gate_jumps():
    with pytest.raises(ValueError, match="Human approval"):
        manifest(round_trip_state="HUMAN_APPROVED", qa_receipt_hashes=[H1])
    with pytest.raises(ValueError, match="pre-approval"):
        manifest(human_approval_sha256=H1)
    with pytest.raises(ValueError, match="only PLACEMENT_BOUND"):
        manifest(resolve_placement_plan_sha256=H2)
    with pytest.raises(ValueError, match="untreated source"):
        manifest(untreated_source_preserved=False)
    with pytest.raises(ValueError, match="downstream effects"):
        manifest(asset_promotion_started=True)


def test_preflight_ready_and_fail_closed_precedence():
    p, cap, src = policy(), capability(), source()
    session = plan([src.record_sha256], cap.record_sha256)
    ready = raf.classify_preflight(policy=p, capability=cap, plan=session,
                                   sources=(src,), evaluated_at=NOW)
    assert ready["decision"] == "READY_FOR_OWNER_HUMAN_GATE"
    assert not any(ready[key] for key in ready if key.endswith("_started") or key.endswith("_launched"))

    blocked_src = source(rights_state="REVOKED")
    unknown_cap = capability(license_state="UNKNOWN")
    blocked_plan = plan([blocked_src.record_sha256], unknown_cap.record_sha256)
    result = raf.classify_preflight(policy=p, capability=unknown_cap,
                                    plan=blocked_plan, sources=(blocked_src,), evaluated_at=NOW)
    assert result["decision"] == "BLOCKED"
    assert "SOURCE_RIGHTS_NOT_PASS" in result["reason_codes"]
    assert "LICENSE_STATE_NOT_VERIFIED" in result["reason_codes"]


def test_source_set_order_duplicate_and_cap_are_rejected():
    cap = capability()
    with pytest.raises(ValueError, match="canonical sorted"):
        plan([H2, H1], cap.record_sha256)
    with pytest.raises(ValueError, match="unique"):
        plan([H1, H1], cap.record_sha256)


def test_public_projection_is_body_path_license_and_inventory_free():
    projection = raf.public_projection(capability())
    assert projection["body_included"] is False
    assert projection["absolute_path_included"] is False
    assert projection["license_data_included"] is False
    assert projection["private_plugin_inventory_included"] is False
    assert "executable_sha256" not in projection
    assert "plugin_inventory_sha256" not in projection


def test_static_effect_surface_is_all_false():
    assert raf.EFFECT_SURFACE
    assert set(raf.EFFECT_SURFACE.values()) == {False}
    source_text = Path(raf.__file__).read_text(encoding="utf-8")
    for forbidden in ("subprocess", "os.system", "requests", "urllib", "open(", "Path.write"):
        assert forbidden not in source_text
