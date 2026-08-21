from __future__ import annotations

from dataclasses import replace

import pytest

from ai_video_production.dbd_gold_kpi import (
    ClaimValidatorStatus, DbDGoldKpiEvaluator, DbDGoldManifest,
    GoldAcceptanceStatus, GoldCorrection, GoldDomain, GoldMatch, GoldPrediction,
    GoldRejection, GoldSplit, PILOT_REQUIRED_DOMAINS, RECOGNITION_KPI_DOMAINS,
)


def _match(index: int, split: GoldSplit, *, real: bool = True, complete: bool = True) -> GoldMatch:
    domains = PILOT_REQUIRED_DOMAINS | RECOGNITION_KPI_DOMAINS if complete else {GoldDomain.HOOK}
    return GoldMatch(
        f"match-{index}", f"source-{index}", f"media://owned/match-{index}",
        f"rights://owner/match-{index}", split, "9.1.0", "hud-2.3.0",
        frozenset(domains), real, f"human://labeler-{index}",
    )


def _manifest(*, real: bool = True, count: int = 5) -> DbDGoldManifest:
    return DbDGoldManifest(
        "dbd-pilot", 1, "detector-1", "model-1",
        tuple(_match(i, GoldSplit.TEST if i == count else GoldSplit.TRAIN, real=real) for i in range(1, count + 1)),
    )


def _predictions() -> tuple[GoldPrediction, ...]:
    return tuple(
        GoldPrediction(
            f"sample-{domain.value.lower()}", "match-5", domain, "expected", "expected",
            False, 900, 12, False, True, ClaimValidatorStatus.VERIFIED,
            f"knowledge://validated/{domain.value.lower()}",
        )
        for domain in sorted(RECOGNITION_KPI_DOMAINS, key=lambda x: x.value)
    )


def test_complete_held_out_manifest_metrics_are_deterministic_but_need_claim_authority() -> None:
    report = DbDGoldKpiEvaluator.evaluate(_manifest(), _predictions())
    assert report.acceptance_status is GoldAcceptanceStatus.NOT_CONFIRMED
    assert report.reason_codes == ("PRODUCTION_ACCURACY_AUTHORITY_NOT_GRANTED",)
    assert report.production_accuracy_claim_authorized is False
    assert report.held_out_case_count == len(RECOGNITION_KPI_DOMAINS)
    assert all(x.precision_milli == 1000 and x.recall_milli == 1000 for x in report.domain_kpis)
    assert all(x.calibration_error_milli == 100 and x.stability_milli == 1000 for x in report.domain_kpis)
    assert report.dataset_sha256.startswith("sha256:")

    authorized = DbDGoldKpiEvaluator.evaluate(
        _manifest(), _predictions(), production_accuracy_claim_authorized=True,
    )
    assert authorized.acceptance_status is GoldAcceptanceStatus.PASS
    assert authorized.production_accuracy_claim_authorized is True


def test_incomplete_or_non_real_pilot_stays_not_confirmed_and_cannot_claim_accuracy() -> None:
    manifest = DbDGoldManifest(
        "incomplete", 1, "detector-1", "model-1",
        (_match(1, GoldSplit.TRAIN, real=False, complete=False),),
    )
    report = DbDGoldKpiEvaluator.evaluate(manifest, ())
    assert report.acceptance_status is GoldAcceptanceStatus.NOT_CONFIRMED
    assert "PILOT_MATCH_COUNT_OUTSIDE_5_TO_10" in report.reason_codes
    assert "REAL_MEDIA_EVIDENCE_INCOMPLETE" in report.reason_codes
    assert "HELD_OUT_TEST_SPLIT_MISSING" in report.reason_codes
    with pytest.raises(ValueError, match="complete held-out"):
        DbDGoldKpiEvaluator.evaluate(manifest, (), production_accuracy_claim_authorized=True)


def test_wrong_unknown_contradiction_latency_and_unvalidated_claim_are_reported() -> None:
    rows = list(_predictions())
    rows[0] = replace(
        rows[0], predicted_label="wrong", contradiction=True,
        validator_status=ClaimValidatorStatus.REJECTED, validator_source_ref="knowledge://rejected/claim",
        latency_ms=30, replay_consistent=False,
    )
    rows[1] = replace(rows[1], predicted_label=None, abstained=True, confidence_milli=100)
    report = DbDGoldKpiEvaluator.evaluate(_manifest(), rows)
    by_domain = {x.domain: x for x in report.domain_kpis}
    wrong = by_domain[rows[0].domain]
    unknown = by_domain[rows[1].domain]
    assert (wrong.false_positive, wrong.false_negative, wrong.contradiction_count, wrong.invalid_claim_count) == (1, 1, 1, 1)
    assert unknown.unknown_count == 1
    assert wrong.mean_latency_ms == 30
    assert wrong.stability_milli == 0
    assert "UNVALIDATED_PREDICTION_CLAIM" in report.reason_codes
    assert "RECALL_BELOW_THRESHOLD" in report.reason_codes
    assert "CALIBRATION_ERROR_ABOVE_THRESHOLD" in report.reason_codes
    assert "REPLAY_STABILITY_BELOW_THRESHOLD" in report.reason_codes
    with pytest.raises(ValueError, match="complete held-out"):
        DbDGoldKpiEvaluator.evaluate(
            _manifest(), rows, production_accuracy_claim_authorized=True,
        )


def test_manifest_rejects_split_leakage_and_prediction_scope_mismatch() -> None:
    with pytest.raises(ValueError, match="leakage"):
        DbDGoldManifest(
            "leak", 1, "detector", "model",
            (
                _match(1, GoldSplit.TRAIN),
                replace(_match(2, GoldSplit.TEST), source_group_id="source-1"),
            ),
        )
    bad = replace(_predictions()[0], match_id="missing-match")
    with pytest.raises(ValueError, match="declared match/domain"):
        DbDGoldKpiEvaluator.evaluate(_manifest(), (bad,))


def test_corrections_preserve_original_corrected_reviewer_reason_and_provenance() -> None:
    correction = GoldCorrection(
        "correction-1", _predictions()[0].sample_id, "wrong", "expected",
        "human://reviewer-1", "WRONG_IDENTITY", "evidence://review/frame-10",
    )
    report = DbDGoldKpiEvaluator.evaluate(_manifest(), _predictions(), (correction,))
    assert report.correction_candidate_ids == ("correction-1",)
    with pytest.raises(ValueError, match="must change"):
        replace(correction, corrected_label="wrong")
    with pytest.raises(ValueError, match="evaluated sample"):
        DbDGoldKpiEvaluator.evaluate(
            _manifest(), _predictions(), (replace(correction, sample_id="sample-missing"),),
        )


def test_rejection_reasons_are_durable_and_queryable() -> None:
    rejected = (
        GoldRejection("reject-1", "candidate://one", GoldDomain.MAP, "RIGHTS_UNKNOWN", "human://reviewer-1", "evidence://review/one"),
        GoldRejection("reject-2", "candidate://two", GoldDomain.KILLER, "RIGHTS_UNKNOWN", "human://reviewer-1", "evidence://review/two"),
        GoldRejection("reject-3", "candidate://three", GoldDomain.PERK, "UNRELATED", "human://reviewer-2", "evidence://review/three"),
    )
    report = DbDGoldKpiEvaluator.evaluate(_manifest(), _predictions(), rejections=rejected)
    assert report.rejection_reason_counts == (("RIGHTS_UNKNOWN", 2), ("UNRELATED", 1))
    with pytest.raises(ValueError, match="rejection_id values must be unique"):
        DbDGoldKpiEvaluator.evaluate(
            _manifest(), _predictions(), rejections=(rejected[0], rejected[0]),
        )


def test_gold_provenance_is_human_traceable_and_secret_refs_fail_closed() -> None:
    with pytest.raises(ValueError, match="source_ref must use media"):
        replace(_match(1, GoldSplit.TEST), source_ref="synthetic://match-1")
    with pytest.raises(ValueError, match="labeler_ref must use human"):
        replace(_match(1, GoldSplit.TEST), labeler_ref="automation://labeler-1")
    with pytest.raises(ValueError, match="must not disclose"):
        replace(_predictions()[0], validator_source_ref="secret://token-name")
    with pytest.raises(ValueError, match="reviewer_ref must use human"):
        GoldCorrection(
            "correction-unsafe", _predictions()[0].sample_id, "wrong", "expected",
            "automation://reviewer", "WRONG_IDENTITY", "evidence://review/frame-10",
        )
    with pytest.raises(ValueError, match="must not disclose"):
        GoldRejection(
            "reject-unsafe", "credential://provider/key", GoldDomain.MAP,
            "UNSAFE_REFERENCE", "human://reviewer-1", "evidence://review/unsafe",
        )
