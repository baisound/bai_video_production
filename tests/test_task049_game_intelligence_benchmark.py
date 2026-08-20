from __future__ import annotations

import pytest

from ai_video_production.canonical_game_event import GameEventType
from ai_video_production.game_event_evidence import SourceFrameRange
from ai_video_production.game_intelligence_benchmark import (
    BenchmarkDatasetKind,
    EventBenchmarkCase,
    EventBenchmarkDataset,
    EventBenchmarkEvaluator,
    EventBenchmarkPrediction,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


def dataset(kind: BenchmarkDatasetKind = BenchmarkDatasetKind.SYNTHETIC) -> EventBenchmarkDataset:
    label = "human://reviewer-1" if kind is BenchmarkDatasetKind.HUMAN_GOLD else None
    cases = (
        EventBenchmarkCase("case-001", "fixture://1", GameEventType.WINDOW_VAULT, SourceFrameRange(100, 110), labeler_ref=label),
        EventBenchmarkCase("case-002", "fixture://2", GameEventType.HOOK, SourceFrameRange(200, 205), labeler_ref=label),
        EventBenchmarkCase("case-003", "fixture://3", None, None, labeler_ref=label),
        EventBenchmarkCase("case-004", "fixture://4", None, None, expected_abstention=True, labeler_ref=label),
    )
    return EventBenchmarkDataset("dbd-event-fixture", 1, kind, cases)


def test_benchmark_computes_precision_recall_f1_unknown_and_timing_without_accuracy_authority() -> None:
    ds = dataset()
    predictions = (
        EventBenchmarkPrediction("case-001", GameEventType.WINDOW_VAULT, 900, SourceFrameRange(101, 111)),
        EventBenchmarkPrediction("case-002", GameEventType.INJURY, 800, SourceFrameRange(200, 205)),
        EventBenchmarkPrediction("case-003", None, 100),
        EventBenchmarkPrediction("case-004", None, 200, abstained=True),
    )
    report = EventBenchmarkEvaluator.evaluate(ds, predictions)
    assert report.true_positive == 1
    assert report.false_positive == 1
    assert report.false_negative == 1
    assert report.true_negative == 2
    assert report.precision_milli == 500
    assert report.recall_milli == 500
    assert report.f1_milli == 500
    assert report.unknown_detection_rate_milli == 1000
    assert report.abstention_correctness_milli == 1000
    assert report.mean_start_error_frames_milli == 1000
    assert report.mean_end_error_frames_milli == 1000
    payload = report.to_dict()
    assert payload["native_media_evidence"] is False
    assert payload["production_accuracy_claim_authorized"] is False
    body = dict(payload)
    digest = body.pop("benchmark_report_sha256")
    assert digest == sha256_bytes(canonical_json_bytes(body))


def test_wrong_class_counts_as_false_positive_and_false_negative() -> None:
    ds = EventBenchmarkDataset(
        "single-case",
        1,
        BenchmarkDatasetKind.SYNTHETIC,
        (EventBenchmarkCase("case-001", "fixture://1", GameEventType.HOOK, SourceFrameRange(1, 2)),),
    )
    report = EventBenchmarkEvaluator.evaluate(
        ds,
        (EventBenchmarkPrediction("case-001", GameEventType.INJURY, 900, SourceFrameRange(1, 2)),),
    )
    assert report.true_positive == 0
    assert report.false_positive == 1
    assert report.false_negative == 1
    assert report.precision_milli == 0
    assert report.recall_milli == 0


def test_expected_unknown_case_measures_abstention_and_false_assertion() -> None:
    ds = EventBenchmarkDataset(
        "unknown-case",
        1,
        BenchmarkDatasetKind.SYNTHETIC,
        (EventBenchmarkCase("case-001", "fixture://ambiguous", None, None, expected_abstention=True),),
    )
    ok = EventBenchmarkEvaluator.evaluate(ds, (EventBenchmarkPrediction("case-001", None, 100, abstained=True),))
    assert ok.unknown_detection_rate_milli == 1000
    assert ok.false_positive == 0

    bad = EventBenchmarkEvaluator.evaluate(ds, (EventBenchmarkPrediction("case-001", GameEventType.HOOK, 990),))
    assert bad.unknown_detection_rate_milli == 0
    assert bad.false_positive == 1


def test_human_gold_requires_labeler_provenance() -> None:
    with pytest.raises(ValueError, match="labeler_ref"):
        EventBenchmarkDataset(
            "gold",
            1,
            BenchmarkDatasetKind.HUMAN_GOLD,
            (EventBenchmarkCase("case-001", "media://1", GameEventType.HOOK, SourceFrameRange(1, 2)),),
        )
    gold = dataset(BenchmarkDatasetKind.HUMAN_GOLD)
    assert gold.kind is BenchmarkDatasetKind.HUMAN_GOLD
    assert all(case.labeler_ref for case in gold.cases)


def test_prediction_set_must_exactly_match_dataset() -> None:
    ds = dataset()
    with pytest.raises(ValueError, match="exactly match"):
        EventBenchmarkEvaluator.evaluate(ds, (EventBenchmarkPrediction("case-001", None, 0),))
    with pytest.raises(ValueError, match="unique"):
        EventBenchmarkEvaluator.evaluate(
            EventBenchmarkDataset(
                "tiny", 1, BenchmarkDatasetKind.SYNTHETIC,
                (EventBenchmarkCase("case-001", "fixture://1", None, None),),
            ),
            (EventBenchmarkPrediction("case-001", None, 0), EventBenchmarkPrediction("case-001", None, 0)),
        )


def test_abstained_prediction_cannot_smuggle_type_or_range() -> None:
    with pytest.raises(ValueError, match="cannot assert"):
        EventBenchmarkPrediction("case-001", GameEventType.HOOK, 100, abstained=True)
    with pytest.raises(ValueError, match="requires predicted_event_type"):
        EventBenchmarkPrediction("case-001", None, 100, SourceFrameRange(1, 2))


def test_synthetic_dataset_hash_is_deterministic_and_not_a_gold_claim() -> None:
    ds = dataset()
    first = ds.to_dict()
    second = ds.to_dict()
    assert first == second
    body = dict(first)
    digest = body.pop("dataset_sha256")
    assert digest == sha256_bytes(canonical_json_bytes(body))
    report = EventBenchmarkEvaluator.evaluate(
        ds,
        (
            EventBenchmarkPrediction("case-001", None, 0, abstained=True),
            EventBenchmarkPrediction("case-002", None, 0, abstained=True),
            EventBenchmarkPrediction("case-003", None, 0),
            EventBenchmarkPrediction("case-004", None, 0, abstained=True),
        ),
    )
    assert report.to_dict()["production_accuracy_claim_authorized"] is False
