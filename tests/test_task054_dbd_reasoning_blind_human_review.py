from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from ai_video_production.dbd_reasoning_blind_human_review import (
    BlindArmMapping,
    BlindCandidate,
    BlindCandidateScore,
    BlindHumanReviewAuthorityBinding,
    BlindHumanReviewSubmission,
    BlindLabel,
    BlindPreference,
    BlindPresentationSample,
    BlindRevealSample,
    admit_blind_human_review_authority_binding,
    admit_blind_human_review_submission,
    admit_blind_review_presentation,
    admit_blind_review_reveal_manifest,
    create_blind_review_pack,
)
from ai_video_production.dbd_reasoning_dataset_leakage import (
    DbDReasoningDatasetLeakageReport,
    LeakageAuditStatus,
)
from ai_video_production.dbd_reasoning_offline_evaluation import (
    DbDReasoningOfflineEvaluationHarness,
    OfflineArmEvidence,
    OfflineEvaluationArm,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
PACK_REF = "blind-review-pack://sha256/" + "e" * 64
SAMPLE_REF = "eval-sample://sha256/" + "f" * 64
REVIEWER_REF = "reviewer://sha256/" + "1" * 64
CONFIRMATION_REF = "human-confirmation://dbd-blind-review/01ARZ3NDEKTSV4RRFFQ69G5FAV"
SEEDS = (104729, 130363, 155921)
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "dbd-reasoning-blind-human-review.schema.json"
MIRROR_PATH = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA_PATH.name


def _offline_report(*, tuned_safe_negative_count: int = 10):
    leakage = DbDReasoningDatasetLeakageReport(
        rights_manifest_sha256=SHA_A,
        audited_segments_sha256=SHA_A,
        segment_count=2,
        split_count=2,
        findings=(),
        status=LeakageAuditStatus.PASS,
    )
    refs = {
        OfflineEvaluationArm.BASELINE: "baseline://dbd/r4e",
        OfflineEvaluationArm.GENERIC: "generic://dbd/r4e",
        OfflineEvaluationArm.TUNED: "model-quarantine://dbd/r4e",
    }
    hashes = {
        OfflineEvaluationArm.BASELINE: SHA_A,
        OfflineEvaluationArm.GENERIC: SHA_B,
        OfflineEvaluationArm.TUNED: SHA_C,
    }
    arms = []
    for arm in OfflineEvaluationArm:
        safe_count = tuned_safe_negative_count if arm is OfflineEvaluationArm.TUNED else 10
        arms.append(OfflineArmEvidence(
            arm=arm,
            binding_ref=refs[arm],
            binding_sha256=hashes[arm],
            output_evidence_set_sha256=hashes[arm],
            sample_count=10,
            observation_count=30,
            schema_valid_count=30,
            unsupported_admitted_fact_count=0,
            patch_incompatible_claim_count=0,
            citation_required_count=30,
            citation_covered_count=30,
            secret_pii_leak_count=0,
            split_leakage_count=0,
            replay_comparison_count=20,
            replay_stable_count=19,
            safe_negative_count=safe_count,
            safe_negative_abstained_count=safe_count,
            latency_p95_ms=200,
            total_cost_milli=100,
            peak_memory_mib=512,
        ))
    return DbDReasoningOfflineEvaluationHarness.evaluate(
        leakage_report=leakage,
        test_sample_set_sha256=SHA_D,
        seeds=SEEDS,
        arms=tuple(arms),
    )


def _pack(*, repeated_output: bool = False):
    report = _offline_report()
    outputs = (SHA_A, SHA_A if repeated_output else SHA_B, SHA_C)
    presentation_sample = BlindPresentationSample(
        SAMPLE_REF,
        tuple(BlindCandidate(label, digest) for label, digest in zip(BlindLabel, outputs, strict=True)),
    )
    by_arm = {item.arm: item for item in report.evaluations}
    arm_order = (OfflineEvaluationArm.TUNED, OfflineEvaluationArm.BASELINE, OfflineEvaluationArm.GENERIC)
    reveal_sample = BlindRevealSample(
        SAMPLE_REF,
        tuple(
            BlindArmMapping(
                label=label,
                arm=arm,
                binding_sha256=by_arm[arm].binding_sha256,
                output_evidence_set_sha256=by_arm[arm].output_evidence_set_sha256,
                candidate_output_sha256=digest,
            )
            for label, arm, digest in zip(BlindLabel, arm_order, outputs, strict=True)
        ),
    )
    presentation, reveal = create_blind_review_pack(
        offline_report=report,
        pack_ref=PACK_REF,
        presentation_samples=(presentation_sample,),
        reveal_samples=(reveal_sample,),
    )
    return report, presentation, reveal


def _submission(presentation, **changes: object) -> BlindHumanReviewSubmission:
    candidates = presentation.samples[0].candidates
    values: dict[str, object] = {
        "offline_evaluation_report_sha256": presentation.offline_evaluation_report_sha256,
        "presentation_sha256": presentation.to_dict()["presentation_sha256"],
        "pack_ref": presentation.pack_ref,
        "sample_ref": SAMPLE_REF,
        "reviewer_ref": REVIEWER_REF,
        "scores": tuple(
            BlindCandidateScore(
                label=item.label,
                candidate_output_sha256=item.candidate_output_sha256,
                factual_acceptable=True,
                uncertainty_handling=4,
                usefulness=4,
                timing=4,
                naturalness=4,
                density=4,
            )
            for item in candidates
        ),
        "preference": BlindPreference.A,
        "reason_codes": (),
        "reviewer_kind": "HUMAN",
        "confirmation_ref": CONFIRMATION_REF,
        "confirmation_sha256": SHA_D,
        "one_shot": True,
        "reviewed_at": "2026-08-25T00:00:00Z",
    }
    values.update(changes)
    return BlindHumanReviewSubmission(**values)


def _authority(record: dict[str, object], **changes: object) -> BlindHumanReviewAuthorityBinding:
    values: dict[str, object] = {
        "presentation_sha256": record["presentation_sha256"],
        "pack_ref": record["pack_ref"],
        "sample_ref": record["sample_ref"],
        "reviewer_ref": record["reviewer_ref"],
        "expected_submission_sha256": record["submission_sha256"],
        "confirmation_ref": record["confirmation_ref"],
        "confirmation_revision": 1,
        "confirmation_sha256": record["confirmation_sha256"],
        "authority_evidence_ref": "human-evidence://dbd-blind-review/sha256/" + "2" * 64,
        "authority_evidence_sha256": SHA_B,
        "reviewer_kind": "HUMAN",
        "decided_at": record["reviewed_at"],
        "expires_at": "2026-08-25T00:10:00Z",
        "one_shot": True,
    }
    values.update(changes)
    return BlindHumanReviewAuthorityBinding(**values)


def _admit(record: dict[str, object], presentation, *, authority=None, evaluated_at="2026-08-25T00:05:00Z"):
    authority = authority or _authority(record)
    return admit_blind_human_review_submission(
        record,
        presentation=presentation,
        authority_record=authority.to_dict(),
        evaluated_at=evaluated_at,
    )


def test_pack_keeps_presentation_blind_and_reveal_sealed() -> None:
    report, presentation, reveal = _pack()
    visible = json.dumps(presentation.to_dict())
    assert all(term not in visible for term in ("BASELINE", "GENERIC", "TUNED", "binding"))
    assert reveal.reveal_state == "SEALED_UNTIL_SUBMISSIONS_ADMITTED"
    assert [item.arm for item in reveal.samples[0].mappings] == [
        OfflineEvaluationArm.TUNED,
        OfflineEvaluationArm.BASELINE,
        OfflineEvaluationArm.GENERIC,
    ]
    assert admit_blind_review_presentation(presentation.to_dict()) == presentation
    assert admit_blind_review_reveal_manifest(
        reveal.to_dict(), presentation=presentation, offline_report=report
    ) == reveal


def test_same_output_from_two_arms_remains_reviewable() -> None:
    _, presentation, _ = _pack(repeated_output=True)
    assert presentation.samples[0].candidates[0].candidate_output_sha256 == (
        presentation.samples[0].candidates[1].candidate_output_sha256
    )


def test_pack_requires_pass_tuned_r4d_gate() -> None:
    _, presentation, reveal = _pack()
    incomplete = _offline_report(tuned_safe_negative_count=0)
    with pytest.raises(ValueError, match="PASS TUNED"):
        create_blind_review_pack(
            offline_report=incomplete,
            pack_ref=PACK_REF,
            presentation_samples=presentation.samples,
            reveal_samples=reveal.samples,
        )


def test_crossed_reveal_mapping_fails_closed() -> None:
    report, presentation, reveal = _pack()
    first = reveal.samples[0].mappings[0]
    crossed = replace(first, binding_sha256=SHA_A)
    reveal_sample = replace(reveal.samples[0], mappings=(crossed, *reveal.samples[0].mappings[1:]))
    with pytest.raises(ValueError, match="crosses"):
        create_blind_review_pack(
            offline_report=report,
            pack_ref=PACK_REF,
            presentation_samples=presentation.samples,
            reveal_samples=(reveal_sample,),
        )


def test_submission_is_exact_blind_body_free_human_evidence() -> None:
    _, presentation, _ = _pack()
    submission = _submission(presentation)
    record = submission.to_dict()
    admitted = _admit(record, presentation)
    assert admitted == submission
    serialized = json.dumps(record)
    assert all(term not in serialized for term in ("BASELINE", "GENERIC", "TUNED", "model", "transcript"))
    assert submission.submission_state == "BLIND_HUMAN_EVIDENCE_NO_PROMOTION"
    assert not hasattr(submission, "promote")


def test_submission_candidate_pack_and_checksum_crossing_fail_closed() -> None:
    _, presentation, _ = _pack()
    record = _submission(presentation).to_dict()
    crossed = json.loads(json.dumps(record))
    crossed["scores"][0]["candidate_output_sha256"] = SHA_D
    with pytest.raises(ValueError, match="candidate outputs"):
        _admit(crossed, presentation, authority=_authority(record))
    with pytest.raises(ValueError, match="crosses"):
        _admit({**record, "pack_ref": "blind-review-pack://sha256/" + "0" * 64}, presentation, authority=_authority(record))
    with pytest.raises(ValueError, match="checksum"):
        _admit({**record, "submission_sha256": SHA_A}, presentation, authority=_authority(record))


def test_human_confirmation_scores_and_blind_reason_codes_fail_closed() -> None:
    _, presentation, _ = _pack()
    with pytest.raises(ValueError, match="external Human"):
        replace(_submission(presentation), reviewer_kind="AI")
    with pytest.raises(ValueError, match="1 through 5"):
        replace(_submission(presentation).scores[0], naturalness=6)
    with pytest.raises(ValueError, match="non-blind"):
        replace(_submission(presentation), reason_codes=("TUNED_MODEL_BEST",))
    with pytest.raises(ValueError, match="requires"):
        replace(_submission(presentation), preference=BlindPreference.ALL_REJECTED)
    rejected = replace(
        _submission(presentation),
        preference=BlindPreference.ALL_REJECTED,

        reason_codes=("ALL_CANDIDATES_UNACCEPTABLE",),
    )
    assert rejected.preference is BlindPreference.ALL_REJECTED


def test_external_human_authority_is_exact_one_shot_and_time_bounded() -> None:
    _, presentation, _ = _pack()
    record = _submission(presentation).to_dict()
    authority = _authority(record)
    assert admit_blind_human_review_authority_binding(authority.to_dict()) == authority
    with pytest.raises(ValueError, match="exact blind submission"):
        _admit(record, presentation, authority=replace(authority, reviewer_ref="reviewer://sha256/" + "3" * 64))
    with pytest.raises(ValueError, match="expired"):
        _admit(record, presentation, authority=authority, evaluated_at="2026-08-25T00:10:00Z")
    with pytest.raises(ValueError, match="not yet"):
        _admit(record, presentation, authority=authority, evaluated_at="2026-08-24T23:59:59Z")
    with pytest.raises(ValueError, match="one-shot Human"):
        replace(authority, reviewer_kind="AI")
    with pytest.raises(ValueError, match="checksum"):
        admit_blind_human_review_authority_binding({**authority.to_dict(), "binding_sha256": SHA_A})


def test_presentation_and_reveal_tamper_or_unknown_fields_fail_closed() -> None:
    report, presentation, reveal = _pack()
    with pytest.raises(ValueError, match="shape"):
        admit_blind_review_presentation({**presentation.to_dict(), "arm": "TUNED"})
    with pytest.raises(ValueError, match="checksum"):
        admit_blind_review_presentation({**presentation.to_dict(), "presentation_sha256": SHA_A})
    crossed = json.loads(json.dumps(reveal.to_dict()))
    crossed["samples"][0]["mappings"][0]["candidate_output_sha256"] = SHA_D
    with pytest.raises(ValueError):
        admit_blind_review_reveal_manifest(crossed, presentation=presentation, offline_report=report)


def test_schema_mirror_validates_all_three_exact_record_kinds() -> None:
    report, presentation, reveal = _pack()
    submission = _submission(presentation)
    authority = _authority(submission.to_dict())
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    mirror = json.loads(MIRROR_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    assert mirror == schema
    for record in (presentation.to_dict(), reveal.to_dict(), submission.to_dict(), authority.to_dict()):
        assert list(validator.iter_errors(record)) == []
    leaked = dict(presentation.to_dict())
    leaked["arm"] = "TUNED"
    assert list(validator.iter_errors(leaked))
    invalid = dict(submission.to_dict())
    invalid["reviewer_ref"] = "reviewer://John-Doe"
    assert list(validator.iter_errors(invalid))
    assert report.tuned_gate_status.value == "PASS"
