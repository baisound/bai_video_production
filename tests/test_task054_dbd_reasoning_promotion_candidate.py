from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from ai_video_production.dbd_reasoning_blind_human_review import BlindCandidateScore, BlindPreference
from ai_video_production.dbd_reasoning_promotion_candidate import (
    BlindReviewEvidence,
    DbDReasoningPromotionCandidateEvaluator,
    PromotionCandidateStatus,
    admit_dbd_reasoning_promotion_candidate_report,
)
from ai_video_production.dbd_reasoning_offline_evaluation import OfflineEvaluationArm
from test_task054_dbd_reasoning_blind_human_review import (
    SHA_A,
    _authority,
    _pack,
    _submission,
)


REVIEWER_1 = "reviewer://sha256/" + "1" * 64
REVIEWER_2 = "reviewer://sha256/" + "2" * 64
REVIEWER_3 = "reviewer://sha256/" + "3" * 64
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "dbd-reasoning-promotion-candidate-report.schema.json"
MIRROR_PATH = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA_PATH.name


def _evidence(presentation, reviewer_ref: str, index: int, *, preference=BlindPreference.A,
              tuned_factual=True, tuned_style=5, baseline_style=4) -> BlindReviewEvidence:
    original = _submission(presentation)
    scores = []
    for score in original.scores:
        style = tuned_style if score.label.value == "A" else baseline_style if score.label.value == "B" else 4
        scores.append(BlindCandidateScore(
            label=score.label,
            candidate_output_sha256=score.candidate_output_sha256,
            factual_acceptable=tuned_factual if score.label.value == "A" else True,
            uncertainty_handling=style,
            usefulness=style,
            timing=style,
            naturalness=style,
            density=style,
        ))
    confirmation_ref = (
        "human-confirmation://dbd-blind-review/01ARZ3NDEKTSV4RRFFQ69G5FA" + chr(ord("V") + index)
    )
    digest = "sha256:" + str(index + 4) * 64
    submission = replace(
        original,
        reviewer_ref=reviewer_ref,
        scores=tuple(scores),
        preference=preference,
        confirmation_ref=confirmation_ref,
        confirmation_sha256=digest,
    )
    authority = _authority(
        submission.to_dict(),
        authority_evidence_ref="human-evidence://dbd-blind-review/sha256/" + str(index + 6) * 64,
        authority_evidence_sha256="sha256:" + str(index + 6) * 64,
    )
    return BlindReviewEvidence(submission, authority)


def _evaluate(evidence, reviewers=(REVIEWER_1, REVIEWER_2)):
    report, presentation, reveal = _pack()
    return DbDReasoningPromotionCandidateEvaluator.evaluate(
        offline_report=report,
        presentation=presentation,
        reveal_manifest=reveal,
        reviewer_refs=reviewers,
        evidence=tuple(evidence(presentation) if callable(evidence) else evidence),
        evaluated_at="2026-08-25T00:05:00Z",
    )


def test_complete_agreed_nonregressing_improvement_is_owner_review_candidate_only() -> None:
    result = _evaluate(lambda p: (
        _evidence(p, REVIEWER_1, 0),
        _evidence(p, REVIEWER_2, 1),
    ))
    assert result.status is PromotionCandidateStatus.READY_FOR_OWNER_REVIEW
    assert result.preference_agreement_milli == 1000
    by_arm = {item.arm: item for item in result.aggregates}
    assert by_arm[OfflineEvaluationArm.TUNED].preference_count == 2
    assert by_arm[OfflineEvaluationArm.TUNED].style_score_milli == 1000
    assert by_arm[OfflineEvaluationArm.BASELINE].style_score_milli == 800
    assert result.report_state == "PROMOTION_CANDIDATE_ONLY_OWNER_DECISION_REQUIRED"
    assert not hasattr(result, "promote") and not hasattr(result, "approve")


def test_factual_regression_is_noncompensating_not_eligible() -> None:
    result = _evaluate(lambda p: (
        _evidence(p, REVIEWER_1, 0, tuned_factual=False),
        _evidence(p, REVIEWER_2, 1, tuned_factual=False),
    ))
    assert result.status is PromotionCandidateStatus.NOT_ELIGIBLE
    assert "FACTUAL_ACCEPTABILITY_REGRESSION" in result.finding_codes


def test_style_score_must_improve_in_addition_to_preference() -> None:
    result = _evaluate(lambda p: (
        _evidence(p, REVIEWER_1, 0, tuned_style=4, baseline_style=4),
        _evidence(p, REVIEWER_2, 1, tuned_style=4, baseline_style=4),
    ))
    assert result.status is PromotionCandidateStatus.NOT_ELIGIBLE
    assert "STYLE_IMPROVEMENT_NOT_JUSTIFIED" in result.finding_codes


def test_low_inter_reviewer_agreement_is_not_confirmed() -> None:
    result = _evaluate(
        lambda p: (
            _evidence(p, REVIEWER_1, 0, preference=BlindPreference.A),
            _evidence(p, REVIEWER_2, 1, preference=BlindPreference.A),
            _evidence(p, REVIEWER_3, 2, preference=BlindPreference.B),
        ),
        reviewers=(REVIEWER_1, REVIEWER_2, REVIEWER_3),
    )
    assert result.preference_agreement_milli == 333
    assert result.status is PromotionCandidateStatus.NOT_CONFIRMED
    assert result.finding_codes == ("INTER_REVIEWER_AGREEMENT_LOW",)


def test_missing_duplicate_or_unsorted_reviewer_coverage_fails_closed() -> None:
    report, presentation, reveal = _pack()
    first = _evidence(presentation, REVIEWER_1, 0)
    second = _evidence(presentation, REVIEWER_2, 1)
    kwargs = dict(offline_report=report, presentation=presentation, reveal_manifest=reveal,
                  evaluated_at="2026-08-25T00:05:00Z")
    with pytest.raises(ValueError, match="cover"):
        DbDReasoningPromotionCandidateEvaluator.evaluate(
            **kwargs, reviewer_refs=(REVIEWER_1, REVIEWER_2), evidence=(first,)
        )
    with pytest.raises(ValueError, match="cover"):
        DbDReasoningPromotionCandidateEvaluator.evaluate(
            **kwargs, reviewer_refs=(REVIEWER_1, REVIEWER_2), evidence=(first, first)
        )
    with pytest.raises(ValueError, match="sorted"):
        DbDReasoningPromotionCandidateEvaluator.evaluate(
            **kwargs, reviewer_refs=(REVIEWER_2, REVIEWER_1), evidence=(second, first)
        )


def test_confirmation_reuse_fails_closed() -> None:
    report, presentation, reveal = _pack()
    first = _evidence(presentation, REVIEWER_1, 0)
    second = _evidence(presentation, REVIEWER_2, 1)
    reused_submission = replace(
        second.submission,
        confirmation_ref=first.submission.confirmation_ref,
        confirmation_sha256=first.submission.confirmation_sha256,
    )
    reused = BlindReviewEvidence(reused_submission, _authority(reused_submission.to_dict()))
    with pytest.raises(ValueError, match="reused"):
        DbDReasoningPromotionCandidateEvaluator.evaluate(
            offline_report=report, presentation=presentation, reveal_manifest=reveal,
            reviewer_refs=(REVIEWER_1, REVIEWER_2), evidence=(first, reused),
            evaluated_at="2026-08-25T00:05:00Z",
        )


def test_report_exact_readmission_and_decision_forgery_rejected() -> None:
    result = _evaluate(lambda p: (
        _evidence(p, REVIEWER_1, 0),
        _evidence(p, REVIEWER_2, 1),
    ))
    record = result.to_dict()
    assert admit_dbd_reasoning_promotion_candidate_report(record) == result
    forged = json.loads(json.dumps(record))
    forged["status"] = "NOT_ELIGIBLE"
    with pytest.raises(ValueError, match="decision"):
        admit_dbd_reasoning_promotion_candidate_report(forged)
    with pytest.raises(ValueError, match="R4E bound"):
        replace(result, sample_count=1001, submission_count=2002)
    with pytest.raises(ValueError, match="shape"):
        admit_dbd_reasoning_promotion_candidate_report({**record, "promoted": True})
    with pytest.raises(ValueError, match="checksum"):
        admit_dbd_reasoning_promotion_candidate_report({**record, "promotion_candidate_report_sha256": SHA_A})


def test_promotion_candidate_schema_mirror_and_body_free_record() -> None:
    result = _evaluate(lambda p: (
        _evidence(p, REVIEWER_1, 0),
        _evidence(p, REVIEWER_2, 1),
    ))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    mirror = json.loads(MIRROR_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert mirror == schema
    assert list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(result.to_dict())) == []
    serialized = json.dumps(result.to_dict())
    assert "transcript" not in serialized and "commentary" not in serialized
    leaked = dict(result.to_dict())
    leaked["approved"] = True
    assert list(Draft202012Validator(schema).iter_errors(leaked))
