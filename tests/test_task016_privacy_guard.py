from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.privacy_guard import (
    EFFECT_SURFACE,
    ContractState,
    HumanPrivacyReviewBinding,
    NotificationDecision,
    PrivacyDetectorProfileBinding,
    PrivacyEvaluationDecision,
    PrivacyEvaluationReceipt,
    PrivacyEvidenceClaim,
    PrivacyInputBinding,
    PrivacyInvalidationReceipt,
    PrivacyPolicyRevision,
    PrivacyPublicationGateBinding,
    RedactionPlanRevision,
    classify_notification,
    classify_publication_gate,
    create_coordinate,
    create_redaction_operation,
    evaluate_privacy,
    project_public,
    validate_record,
)
from ai_video_production.serialization import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "privacy-guard.schema.json"
MIRROR_PATH = ROOT / "src" / "ai_video_production" / "schema_resources" / "privacy-guard.schema.json"
MODULE_PATH = ROOT / "src" / "ai_video_production" / "privacy_guard.py"
NOW = "2026-08-17T00:00:00Z"


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def state_binding(decision: str = "PASS") -> dict[str, object]:
    return {
        "contract_state": "BOUND_VERIFIED",
        "decision": decision,
        "evaluation_ref": "authority/evaluation/1",
        "evaluation_sha256": digest("external-evaluation" + decision),
        "evaluated_at": NOW,
    }


def coordinate() -> dict[str, object]:
    return create_coordinate(
        coordinate_id="coord-1",
        source_kind="ASSET_REVISION",
        asset_id="asset-1",
        asset_checksum_sha256=digest("asset-bytes"),
        asset_revision_ref="task003/asset-revision/1",
        asset_revision_sha256=digest("asset-revision"),
        transcript_manifest_ref=None,
        transcript_manifest_sha256=None,
        segment_id=None,
        range_start_int=None,
        range_end_exclusive_int=None,
    )


def policy() -> PrivacyPolicyRevision:
    return PrivacyPolicyRevision.create(
        policy_id="privacy-policy-1",
        revision=1,
        parent_record_sha256=None,
        scope="PUBLICATION",
        enabled_finding_kinds=["EMAIL_ADDRESS"],
        block_severities=["HIGH", "CRITICAL"],
        review_severities=["WARNING"],
        max_claim_age_seconds=3600,
        authority_ref="owner/privacy-policy/1",
        authority_sha256=digest("policy-authority"),
        effective_at="2026-08-16T23:00:00Z",
        expires_at=None,
    )


def input_binding(*, rights: str = "PASS", consent: str = "PASS") -> PrivacyInputBinding:
    return PrivacyInputBinding.create(
        binding_id="privacy-input-1",
        production_job_id="production-job-1",
        revision=1,
        parent_record_sha256=None,
        coordinates=[coordinate()],
        rights_binding=state_binding(rights),
        consent_binding=state_binding(consent),
        body_persisted=False,
    )


def detector() -> PrivacyDetectorProfileBinding:
    return PrivacyDetectorProfileBinding.create(
        contract_state="BOUND_VERIFIED",
        profile_ref="privacy/detector-profile/1",
        profile_sha256=digest("detector-profile"),
        detector_id="privacy-detector-1",
        detector_version="1.0.0",
        code_sha256=digest("detector-code"),
        model_ref="privacy/model/1",
        model_sha256=digest("detector-model"),
        supported_finding_kinds=["EMAIL_ADDRESS"],
        capability_state="VERIFIED",
        license_state="PASS",
        evidence_ref="privacy/detector-evidence/1",
        evidence_sha256=digest("detector-evidence"),
        execution_authorized=False,
        execution_started=False,
    )


def claim(
    binding: PrivacyInputBinding,
    profile: PrivacyDetectorProfileBinding,
    *,
    fact_state: str = "NOT_DETECTED",
    severity: str = "INFO",
    coverage_state: str = "COMPLETE",
    observed_at: str = NOW,
) -> PrivacyEvidenceClaim:
    return PrivacyEvidenceClaim.create(
        claim_id="claim-1",
        input_binding_sha256=binding.record_sha256,
        coordinate_sha256=binding.to_dict()["coordinates"][0]["coordinate_sha256"],
        detector_profile_sha256=profile.record_sha256,
        finding_kind="EMAIL_ADDRESS",
        fact_state=fact_state,
        severity=severity,
        coverage_state=coverage_state,
        reason_codes=[],
        confidence_millionths=900_000 if fact_state == "DETECTED" else None,
        private_evidence_ref="privacy/evidence/1",
        private_evidence_sha256=digest("private-evidence"),
        matched_content_sha256=digest("matched") if fact_state == "DETECTED" else None,
        observed_at=observed_at,
        body_persisted=False,
    )


def passing_evaluation() -> tuple[PrivacyPolicyRevision, PrivacyInputBinding, PrivacyDetectorProfileBinding, PrivacyEvaluationReceipt]:
    p, i, d = policy(), input_binding(), detector()
    result = evaluate_privacy(
        evaluation_id="evaluation-1", policy=p, input_binding=i,
        detector_profiles=[d], claims=[claim(i, d)], evaluated_at=NOW,
    )
    return p, i, d, result


def human_review(
    p: PrivacyPolicyRevision,
    i: PrivacyInputBinding,
    evaluation: PrivacyEvaluationReceipt,
    *,
    decision: str = "APPROVE_AS_IS",
    plan_sha256: str | None = None,
) -> HumanPrivacyReviewBinding:
    return HumanPrivacyReviewBinding.create(
        contract_state="BOUND_VERIFIED",
        decision_id="human-review-1",
        decision_revision=1,
        decision_sha256=digest("human-decision"),
        input_binding_sha256=i.record_sha256,
        policy_sha256=p.record_sha256,
        evaluation_sha256=evaluation.record_sha256,
        redaction_plan_sha256=plan_sha256,
        reviewer_kind="HUMAN",
        decision=decision,
        decided_at=NOW,
        evidence_ref="owner/human-privacy-review/1",
        evidence_sha256=digest("human-evidence"),
    )


def test_schema_mirror_is_byte_exact_and_accepts_every_root_type() -> None:
    assert SCHEMA_PATH.read_bytes() == MIRROR_PATH.read_bytes()
    schema = __import__("json").loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    p, i, d, evaluation = passing_evaluation()
    operation = create_redaction_operation(
        operation_id="redaction-operation-1",
        coordinate_sha256=i.to_dict()["coordinates"][0]["coordinate_sha256"],
        action="MASK", replacement_digest=None, reason_codes=["PRIVACY_FINDING"],
    )
    plan = RedactionPlanRevision.create(
        plan_id="redaction-plan-1", revision=1, parent_record_sha256=None,
        input_binding_sha256=i.record_sha256, evaluation_sha256=evaluation.record_sha256,
        operations=[operation], proposal_only=True, mutation_started=False,
        asset_modified=False, transcript_modified=False, srt_modified=False,
    )
    review = human_review(p, i, evaluation)
    notification = classify_notification(
        decision_id="notification-1", input_binding=i, evaluation=evaluation, human_review=review,
    )
    invalidation = PrivacyInvalidationReceipt.create(
        receipt_id="invalidation-1", target_record_type="PrivacyEvaluationReceipt",
        target_ref="privacy/evaluation/1", target_sha256=evaluation.record_sha256,
        reason="POLICY_CHANGED", invalidated_at=NOW,
        replacement_ref=None, replacement_sha256=None, physical_delete_started=False,
    )
    gate = classify_publication_gate(
        gate_id="publication-gate-1", input_binding=i, policy=p, evaluation=evaluation,
        human_review=review, redaction_plan=None, invalidations=[], evaluated_at=NOW,
    )
    records = [p, i, d, claim(i, d), evaluation, plan, review, notification, invalidation, gate]
    assert {record.to_dict()["record_type"] for record in records} == {
        item["$ref"].split("/")[-1] for item in schema["oneOf"]
    }
    for record in records:
        validator.validate(record.to_dict())


def test_canonical_hash_is_deterministic_and_tamper_fails() -> None:
    first = policy()
    second = PrivacyPolicyRevision.from_dict(first.to_dict())
    assert first == second
    tampered = first.to_dict()
    tampered["max_claim_age_seconds"] = 42
    with pytest.raises(ValueError, match="record_sha256 mismatch"):
        PrivacyPolicyRevision.from_dict(tampered)
    with pytest.raises(ValueError, match="unknown Privacy Guard record_type"):
        validate_record({"record_type": "PrivacyMagic", "record_sha256": digest("x")})


def test_complete_not_detected_evidence_is_pass() -> None:
    _, _, _, evaluation = passing_evaluation()
    assert evaluation.to_dict()["decision"] == PrivacyEvaluationDecision.PASS.value
    assert evaluation.to_dict()["reason_codes"] == []


@pytest.mark.parametrize("fact_state", ["NOT_SUPPORTED", "INSUFFICIENT_INPUT", "ERROR", "UNKNOWN"])
def test_unknown_or_unsupported_fact_never_becomes_zero_or_pass(fact_state: str) -> None:
    p, i, d = policy(), input_binding(), detector()
    result = evaluate_privacy(
        evaluation_id="evaluation-unknown", policy=p, input_binding=i,
        detector_profiles=[d], claims=[claim(i, d, fact_state=fact_state, severity="UNKNOWN", coverage_state="UNKNOWN")],
        evaluated_at=NOW,
    )
    assert result.to_dict()["decision"] == "UNKNOWN"
    assert f"FACT_{fact_state}" in result.to_dict()["reason_codes"]


def test_missing_claim_coverage_and_stale_claim_fail_closed() -> None:
    p, i, d = policy(), input_binding(), detector()
    missing = evaluate_privacy(
        evaluation_id="evaluation-missing", policy=p, input_binding=i,
        detector_profiles=[d], claims=[], evaluated_at=NOW,
    )
    stale = evaluate_privacy(
        evaluation_id="evaluation-stale", policy=p, input_binding=i,
        detector_profiles=[d], claims=[claim(i, d, observed_at="2026-08-16T00:00:00Z")],
        evaluated_at=NOW,
    )
    assert missing.to_dict()["decision"] == "UNKNOWN"
    assert "CLAIM_COVERAGE_INCOMPLETE" in missing.to_dict()["reason_codes"]
    assert stale.to_dict()["decision"] == "UNKNOWN"
    assert "CLAIM_STALE" in stale.to_dict()["reason_codes"]


@pytest.mark.parametrize(("severity", "expected"), [("HIGH", "BLOCK"), ("WARNING", "HUMAN_REVIEW_REQUIRED")])
def test_detected_finding_is_policy_classified(severity: str, expected: str) -> None:
    p, i, d = policy(), input_binding(), detector()
    result = evaluate_privacy(
        evaluation_id="evaluation-detected", policy=p, input_binding=i,
        detector_profiles=[d], claims=[claim(i, d, fact_state="DETECTED", severity=severity)],
        evaluated_at=NOW,
    )
    assert result.to_dict()["decision"] == expected


def test_rights_consent_and_detector_admission_are_fail_closed() -> None:
    p, i, d = policy(), input_binding(consent="REVOKED"), detector()
    revoked = evaluate_privacy(
        evaluation_id="evaluation-revoked", policy=p, input_binding=i,
        detector_profiles=[d], claims=[claim(i, d)], evaluated_at=NOW,
    )
    assert revoked.to_dict()["decision"] == "BLOCK"
    unresolved = PrivacyDetectorProfileBinding.create(
        contract_state="CANONICAL_REF_NOT_PROVIDED", profile_ref=None, profile_sha256=None,
        detector_id=None, detector_version=None, code_sha256=None, model_ref=None,
        model_sha256=None, supported_finding_kinds=[], capability_state=None,
        license_state=None, evidence_ref=None, evidence_sha256=None,
        execution_authorized=False, execution_started=False,
    )
    with pytest.raises(ValueError, match="unbound detector"):
        evaluate_privacy(
            evaluation_id="evaluation-detector", policy=p, input_binding=i,
            detector_profiles=[unresolved], claims=[claim(i, d)], evaluated_at=NOW,
        )


def test_claim_must_bind_exact_input_coordinate_and_detector() -> None:
    p, i, d = policy(), input_binding(), detector()
    wrong = claim(i, d).to_dict()
    wrong["coordinate_sha256"] = digest("wrong-coordinate")
    wrong.pop("record_sha256")
    wrong_claim = PrivacyEvidenceClaim.create(**{key: value for key, value in wrong.items() if key != "record_type"})
    with pytest.raises(ValueError, match="claim/input coordinate mismatch"):
        evaluate_privacy(
            evaluation_id="evaluation-wrong", policy=p, input_binding=i,
            detector_profiles=[d], claims=[wrong_claim], evaluated_at=NOW,
        )


def test_redaction_plan_is_proposal_only_and_never_mutates() -> None:
    _, i, _, evaluation = passing_evaluation()
    op = create_redaction_operation(
        operation_id="operation-1",
        coordinate_sha256=i.to_dict()["coordinates"][0]["coordinate_sha256"],
        action="MASK", replacement_digest=None, reason_codes=["PRIVACY_FINDING"],
    )
    plan = RedactionPlanRevision.create(
        plan_id="plan-1", revision=1, parent_record_sha256=None,
        input_binding_sha256=i.record_sha256, evaluation_sha256=evaluation.record_sha256,
        operations=[op], proposal_only=True, mutation_started=False,
        asset_modified=False, transcript_modified=False, srt_modified=False,
    )
    assert plan.to_dict()["proposal_only"] is True
    with pytest.raises(ValueError, match="proposal-only"):
        RedactionPlanRevision.create(
            plan_id="plan-2", revision=1, parent_record_sha256=None,
            input_binding_sha256=i.record_sha256, evaluation_sha256=evaluation.record_sha256,
            operations=[op], proposal_only=True, mutation_started=True,
            asset_modified=False, transcript_modified=False, srt_modified=False,
        )
    with pytest.raises(ValueError, match="replacement_digest"):
        create_redaction_operation(
            operation_id="operation-2", coordinate_sha256=op["coordinate_sha256"],
            action="REPLACE_TEXT", replacement_digest=None, reason_codes=["PRIVACY_FINDING"],
        )


def test_human_review_is_exact_and_ai_cannot_issue_it() -> None:
    p, i, _, evaluation = passing_evaluation()
    fields = human_review(p, i, evaluation).to_dict()
    fields.pop("record_type")
    fields.pop("record_sha256")
    fields["reviewer_kind"] = "AI"
    with pytest.raises(ValueError, match="HUMAN"):
        HumanPrivacyReviewBinding.create(**fields)
    fields["reviewer_kind"] = "HUMAN"
    fields["decision"] = "APPROVE_REDACTION_PLAN"
    with pytest.raises(ValueError, match="requires its exact digest"):
        HumanPrivacyReviewBinding.create(**fields)


def test_notification_and_publication_are_metadata_gates_only() -> None:
    p, i, _, evaluation = passing_evaluation()
    review = human_review(p, i, evaluation)
    notification = classify_notification(
        decision_id="notification-1", input_binding=i, evaluation=evaluation, human_review=review,
    )
    assert notification.to_dict()["send_authorized"] is False
    assert notification.to_dict()["sent"] is False
    gate = classify_publication_gate(
        gate_id="gate-1", input_binding=i, policy=p, evaluation=evaluation,
        human_review=review, redaction_plan=None, invalidations=[], evaluated_at=NOW,
    )
    assert gate.to_dict()["decision"] == "READY_FOR_EXTERNAL_HUMAN_GATE"
    assert gate.to_dict()["publication_started"] is False
    assert gate.to_dict()["release_deploy_started"] is False


def test_invalidation_blocks_publication_without_deleting() -> None:
    p, i, _, evaluation = passing_evaluation()
    review = human_review(p, i, evaluation)
    invalidation = PrivacyInvalidationReceipt.create(
        receipt_id="invalid-1", target_record_type="PrivacyEvaluationReceipt",
        target_ref="privacy/evaluation/1", target_sha256=evaluation.record_sha256,
        reason="POLICY_CHANGED", invalidated_at=NOW,
        replacement_ref=None, replacement_sha256=None, physical_delete_started=False,
    )
    gate = classify_publication_gate(
        gate_id="gate-invalid", input_binding=i, policy=p, evaluation=evaluation,
        human_review=review, redaction_plan=None, invalidations=[invalidation], evaluated_at=NOW,
    )
    assert gate.to_dict()["decision"] == "BLOCKED"
    assert gate.to_dict()["validity_state"] == "INVALIDATED"
    assert invalidation.to_dict()["physical_delete_started"] is False


def test_public_projection_suppresses_private_coordinates_hashes_and_counts() -> None:
    _, binding, detector_binding, _ = passing_evaluation()
    public = project_public(binding)
    for forbidden in ("coordinates", "asset_id", "evidence_ref", "matched_content_sha256", "item_count"):
        assert forbidden not in public
    assert public["body_included"] is False
    assert public["private_coordinates_included"] is False
    detector_public = project_public(detector_binding)
    assert "model_ref" not in detector_public
    assert "profile_ref" not in detector_public


@pytest.mark.parametrize("unsafe", [r"C:\\private\\audio.wav", "/private/audio.wav", "secret/token/1", "../escape"])
def test_body_path_or_credential_like_reference_is_rejected(unsafe: str) -> None:
    fields = state_binding()
    fields["evaluation_ref"] = unsafe
    with pytest.raises(ValueError, match="invalid|body-free"):
        PrivacyInputBinding.create(
            binding_id="unsafe-input", production_job_id="job-1", revision=1,
            parent_record_sha256=None, coordinates=[coordinate()],
            rights_binding=fields, consent_binding=state_binding(), body_persisted=False,
        )


def test_caps_duplicates_and_unknown_fields_are_rejected() -> None:
    base = coordinate()
    duplicate = copy.deepcopy(base)
    with pytest.raises(ValueError, match="unique"):
        PrivacyInputBinding.create(
            binding_id="duplicate-input", production_job_id="job-1", revision=1,
            parent_record_sha256=None, coordinates=[base, duplicate],
            rights_binding=state_binding(), consent_binding=state_binding(), body_persisted=False,
        )
    fields = policy().to_dict()
    fields["raw_text"] = "must never be accepted"
    with pytest.raises(ValueError, match="fields are incomplete or unknown"):
        PrivacyPolicyRevision.from_dict(fields)


def test_static_surface_has_no_io_detector_or_effect_capability() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imported |= {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imported.isdisjoint({"os", "pathlib", "subprocess", "socket", "requests", "httpx", "urllib"})
    assert EFFECT_SURFACE
    assert all(value is False for value in EFFECT_SURFACE.values())
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "raw execution_authorized" not in source
    assert "open(" not in source
