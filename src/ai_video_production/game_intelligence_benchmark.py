"""TASK-049 R10A bounded Gold/Synthetic benchmark contract and KPI evaluator.

The evaluator measures supplied predictions against labelled cases.  It does
not run a detector and never turns synthetic results into a production accuracy
claim.  Real-media/Human-labelled acceptance remains R10B.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from .canonical_game_event import GameEventType
from .game_event_evidence import SourceFrameRange
from .serialization import canonical_json_bytes, sha256_bytes


class BenchmarkDatasetKind(str, Enum):
    SYNTHETIC = "SYNTHETIC"
    HUMAN_GOLD = "HUMAN_GOLD"


def _id_text(value: str, *, field_name: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise ValueError(f"{field_name} must be a non-empty bounded string")
    return value


def _milli(numerator: int, denominator: int) -> int | None:
    if denominator == 0:
        return None
    return (numerator * 1000 + denominator // 2) // denominator


@dataclass(frozen=True, slots=True)
class EventBenchmarkCase:
    case_id: str
    source_ref: str
    expected_event_type: GameEventType | None
    expected_range: SourceFrameRange | None
    expected_abstention: bool = False
    labeler_ref: str | None = None
    evaluation_range: SourceFrameRange | None = None

    def __post_init__(self) -> None:
        _id_text(self.case_id, field_name="case_id", maximum=128)
        _id_text(self.source_ref, field_name="source_ref", maximum=512)
        if self.expected_event_type is not None and not isinstance(self.expected_event_type, GameEventType):
            raise ValueError("expected_event_type must be a GameEventType or None")
        if self.expected_range is not None and not isinstance(self.expected_range, SourceFrameRange):
            raise ValueError("expected_range must be a SourceFrameRange or None")
        if self.expected_event_type is None and self.expected_range is not None:
            raise ValueError("negative/abstention case cannot define expected_range")
        if self.evaluation_range is not None and not isinstance(self.evaluation_range, SourceFrameRange):
            raise ValueError("evaluation_range must be a SourceFrameRange or None")
        if self.expected_range is not None and self.evaluation_range is not None:
            if (
                self.expected_range.start_frame < self.evaluation_range.start_frame
                or self.expected_range.end_frame_exclusive > self.evaluation_range.end_frame_exclusive
            ):
                raise ValueError("expected_range must be contained by evaluation_range")
        if not isinstance(self.expected_abstention, bool):
            raise ValueError("expected_abstention must be bool")
        if self.expected_abstention and self.expected_event_type is not None:
            raise ValueError("expected abstention case must not assert a canonical event type")
        if self.labeler_ref is not None:
            _id_text(self.labeler_ref, field_name="labeler_ref", maximum=256)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "source_ref": self.source_ref,
            "expected_event_type": None if self.expected_event_type is None else self.expected_event_type.value,
            "expected_range": None if self.expected_range is None else self.expected_range.to_dict(),
            "expected_abstention": self.expected_abstention,
            "labeler_ref": self.labeler_ref,
            "evaluation_range": None if self.evaluation_range is None else self.evaluation_range.to_dict(),
        }

    @property
    def native_evaluation_range(self) -> SourceFrameRange | None:
        """Return the bounded real-media window without leaking the expected class.

        Positive legacy cases may use their expected range as the evaluation
        window.  Negative/abstention real-media cases must provide an explicit
        ``evaluation_range`` because they intentionally have no expected event
        range.
        """
        return self.evaluation_range or self.expected_range


@dataclass(frozen=True, slots=True)
class EventBenchmarkDataset:
    dataset_id: str
    revision: int
    kind: BenchmarkDatasetKind
    cases: tuple[EventBenchmarkCase, ...]

    def __post_init__(self) -> None:
        _id_text(self.dataset_id, field_name="dataset_id", maximum=128)
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("revision must be positive")
        if not isinstance(self.kind, BenchmarkDatasetKind):
            raise ValueError("kind must be a BenchmarkDatasetKind")
        if not self.cases or any(not isinstance(item, EventBenchmarkCase) for item in self.cases):
            raise ValueError("cases must contain EventBenchmarkCase values")
        ids = tuple(item.case_id for item in self.cases)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("cases must be unique and canonically sorted by case_id")
        if self.kind is BenchmarkDatasetKind.HUMAN_GOLD and any(not item.labeler_ref for item in self.cases):
            raise ValueError("HUMAN_GOLD cases require labeler_ref provenance")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "dataset_id": self.dataset_id,
            "revision": self.revision,
            "kind": self.kind.value,
            "cases": [item.to_dict() for item in self.cases],
        }
        return {**body, "dataset_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class EventBenchmarkPrediction:
    case_id: str
    predicted_event_type: GameEventType | None
    confidence_milli: int
    predicted_range: SourceFrameRange | None = None
    abstained: bool = False

    def __post_init__(self) -> None:
        _id_text(self.case_id, field_name="case_id", maximum=128)
        if self.predicted_event_type is not None and not isinstance(self.predicted_event_type, GameEventType):
            raise ValueError("predicted_event_type must be a GameEventType or None")
        if isinstance(self.confidence_milli, bool) or not isinstance(self.confidence_milli, int) or not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if self.predicted_range is not None and not isinstance(self.predicted_range, SourceFrameRange):
            raise ValueError("predicted_range must be a SourceFrameRange or None")
        if not isinstance(self.abstained, bool):
            raise ValueError("abstained must be bool")
        if self.abstained and (self.predicted_event_type is not None or self.predicted_range is not None):
            raise ValueError("abstained prediction cannot assert an event type/range")
        if self.predicted_event_type is None and self.predicted_range is not None:
            raise ValueError("prediction range requires predicted_event_type")

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "predicted_event_type": None if self.predicted_event_type is None else self.predicted_event_type.value,
            "confidence_milli": self.confidence_milli,
            "predicted_range": None if self.predicted_range is None else self.predicted_range.to_dict(),
            "abstained": self.abstained,
        }


@dataclass(frozen=True, slots=True)
class EventBenchmarkReport:
    dataset_id: str
    dataset_revision: int
    dataset_kind: BenchmarkDatasetKind
    case_count: int
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    expected_abstention_count: int
    correct_abstention_count: int
    precision_milli: int | None
    recall_milli: int | None
    f1_milli: int | None
    false_positive_rate_milli: int | None
    false_negative_rate_milli: int | None
    unknown_detection_rate_milli: int | None
    abstention_correctness_milli: int
    calibration_error_milli: int | None
    mean_start_error_frames_milli: int | None
    mean_end_error_frames_milli: int | None
    dataset_sha256: str
    native_media_evidence: bool = False
    production_accuracy_claim_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "dataset_id": self.dataset_id,
            "dataset_revision": self.dataset_revision,
            "dataset_kind": self.dataset_kind.value,
            "case_count": self.case_count,
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
            "true_negative": self.true_negative,
            "expected_abstention_count": self.expected_abstention_count,
            "correct_abstention_count": self.correct_abstention_count,
            "precision_milli": self.precision_milli,
            "recall_milli": self.recall_milli,
            "f1_milli": self.f1_milli,
            "false_positive_rate_milli": self.false_positive_rate_milli,
            "false_negative_rate_milli": self.false_negative_rate_milli,
            "unknown_detection_rate_milli": self.unknown_detection_rate_milli,
            "abstention_correctness_milli": self.abstention_correctness_milli,
            "calibration_error_milli": self.calibration_error_milli,
            "mean_start_error_frames_milli": self.mean_start_error_frames_milli,
            "mean_end_error_frames_milli": self.mean_end_error_frames_milli,
            "dataset_sha256": self.dataset_sha256,
            "native_media_evidence": self.native_media_evidence,
            "production_accuracy_claim_authorized": self.production_accuracy_claim_authorized,
        }
        return {**body, "benchmark_report_sha256": sha256_bytes(canonical_json_bytes(body))}


class EventBenchmarkEvaluator:
    """Deterministic micro-metric evaluator for a fixed labelled case set."""

    @staticmethod
    def evaluate(
        dataset: EventBenchmarkDataset,
        predictions: Iterable[EventBenchmarkPrediction],
        *,
        calibration_bins: int = 10,
        native_media_evidence: bool = False,
        production_accuracy_claim_authorized: bool = False,
    ) -> EventBenchmarkReport:
        if not isinstance(dataset, EventBenchmarkDataset):
            raise ValueError("dataset must be an EventBenchmarkDataset")
        if isinstance(calibration_bins, bool) or not isinstance(calibration_bins, int) or not 1 <= calibration_bins <= 100:
            raise ValueError("calibration_bins must be 1..100")
        if not isinstance(native_media_evidence, bool):
            raise ValueError("native_media_evidence must be bool")
        if not isinstance(production_accuracy_claim_authorized, bool):
            raise ValueError("production_accuracy_claim_authorized must be bool")
        if production_accuracy_claim_authorized and (
            dataset.kind is not BenchmarkDatasetKind.HUMAN_GOLD or not native_media_evidence
        ):
            raise ValueError(
                "production accuracy authority requires HUMAN_GOLD native-media evidence"
            )
        prediction_items = tuple(predictions)
        if any(not isinstance(item, EventBenchmarkPrediction) for item in prediction_items):
            raise ValueError("predictions must contain EventBenchmarkPrediction values")
        prediction_map = {item.case_id: item for item in prediction_items}
        if len(prediction_map) != len(prediction_items):
            raise ValueError("prediction case_id values must be unique")
        expected_ids = {item.case_id for item in dataset.cases}
        if set(prediction_map) != expected_ids:
            raise ValueError("prediction case IDs must exactly match the benchmark dataset")

        tp = fp = fn = tn = 0
        expected_abstentions = correct_abstentions = 0
        abstention_matches = 0
        timing_start_errors: list[int] = []
        timing_end_errors: list[int] = []
        calibrated: list[tuple[int, int]] = []  # confidence_milli, correct(0/1)

        for case in dataset.cases:
            pred = prediction_map[case.case_id]
            if pred.abstained == case.expected_abstention:
                abstention_matches += 1
            if case.expected_abstention:
                expected_abstentions += 1
                if pred.abstained:
                    correct_abstentions += 1
            expected_positive = case.expected_event_type is not None
            predicted_positive = pred.predicted_event_type is not None
            exact = bool(
                expected_positive
                and predicted_positive
                and pred.predicted_event_type is case.expected_event_type
                and not pred.abstained
            )
            if predicted_positive:
                calibrated.append((pred.confidence_milli, 1 if exact else 0))
            if exact:
                tp += 1
                if case.expected_range is not None and pred.predicted_range is not None:
                    timing_start_errors.append(abs(pred.predicted_range.start_frame - case.expected_range.start_frame))
                    timing_end_errors.append(abs(pred.predicted_range.end_frame_exclusive - case.expected_range.end_frame_exclusive))
            else:
                if expected_positive:
                    fn += 1
                if predicted_positive:
                    fp += 1
                elif not expected_positive:
                    tn += 1

        precision = _milli(tp, tp + fp)
        recall = _milli(tp, tp + fn)
        f1 = None
        if precision is not None and recall is not None and precision + recall:
            f1 = (2 * precision * recall + (precision + recall) // 2) // (precision + recall)
        fpr = _milli(fp, fp + tn)
        fnr = _milli(fn, fn + tp)
        unknown_rate = _milli(correct_abstentions, expected_abstentions)

        ece = None
        if calibrated:
            weighted_error = 0
            for bin_index in range(calibration_bins):
                low = (bin_index * 1001) // calibration_bins
                high = ((bin_index + 1) * 1001) // calibration_bins
                bucket = [(c, ok) for c, ok in calibrated if low <= c < high]
                if not bucket:
                    continue
                avg_conf = sum(c for c, _ in bucket) // len(bucket)
                avg_acc = _milli(sum(ok for _, ok in bucket), len(bucket))
                assert avg_acc is not None
                weighted_error += abs(avg_conf - avg_acc) * len(bucket)
            ece = (weighted_error + len(calibrated) // 2) // len(calibrated)

        mean_start = None if not timing_start_errors else _milli(sum(timing_start_errors), len(timing_start_errors))
        mean_end = None if not timing_end_errors else _milli(sum(timing_end_errors), len(timing_end_errors))
        # Here *_frames_milli is thousandths of a frame, not a unit interval.

        return EventBenchmarkReport(
            dataset_id=dataset.dataset_id,
            dataset_revision=dataset.revision,
            dataset_kind=dataset.kind,
            case_count=len(dataset.cases),
            true_positive=tp,
            false_positive=fp,
            false_negative=fn,
            true_negative=tn,
            expected_abstention_count=expected_abstentions,
            correct_abstention_count=correct_abstentions,
            precision_milli=precision,
            recall_milli=recall,
            f1_milli=f1,
            false_positive_rate_milli=fpr,
            false_negative_rate_milli=fnr,
            unknown_detection_rate_milli=unknown_rate,
            abstention_correctness_milli=_milli(abstention_matches, len(dataset.cases)) or 0,
            calibration_error_milli=ece,
            mean_start_error_frames_milli=mean_start,
            mean_end_error_frames_milli=mean_end,
            dataset_sha256=dataset.to_dict()["dataset_sha256"],
            native_media_evidence=native_media_evidence,
            production_accuracy_claim_authorized=production_accuracy_claim_authorized,
        )


def _parse_range(value: Any, *, field_name: str) -> SourceFrameRange | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object or null")
    try:
        return SourceFrameRange(
            start_frame=value["start_frame"],
            end_frame_exclusive=value["end_frame_exclusive"],
        )
    except KeyError as exc:
        raise ValueError(f"{field_name} is missing required frame fields") from exc


def parse_event_benchmark_dataset(payload: Any, *, require_hash: bool = True) -> EventBenchmarkDataset:
    """Parse and integrity-check a persisted benchmark dataset.

    R10B Human Gold files are mutable human inputs until saved.  Once a
    ``dataset_sha256`` is present, loading verifies it before accepting labels.
    """
    if not isinstance(payload, dict):
        raise ValueError("benchmark dataset payload must be an object")
    body = dict(payload)
    supplied_hash = body.pop("dataset_sha256", None)
    if require_hash and supplied_hash is None:
        raise ValueError("benchmark dataset requires dataset_sha256")
    if supplied_hash is not None:
        expected_hash = sha256_bytes(canonical_json_bytes(body))
        if supplied_hash != expected_hash:
            raise ValueError("benchmark dataset_sha256 does not match canonical content")
    if body.get("schema_version") != "1.0.0":
        raise ValueError("unsupported benchmark dataset schema_version")
    try:
        kind = BenchmarkDatasetKind(body["kind"])
        raw_cases = body["cases"]
        if not isinstance(raw_cases, list):
            raise ValueError("cases must be an array")
        cases = tuple(
            EventBenchmarkCase(
                case_id=item["case_id"],
                source_ref=item["source_ref"],
                expected_event_type=(
                    None if item.get("expected_event_type") is None
                    else GameEventType(item["expected_event_type"])
                ),
                expected_range=_parse_range(item.get("expected_range"), field_name="expected_range"),
                expected_abstention=item.get("expected_abstention", False),
                labeler_ref=item.get("labeler_ref"),
                evaluation_range=_parse_range(item.get("evaluation_range"), field_name="evaluation_range"),
            )
            for item in raw_cases
        )
        return EventBenchmarkDataset(
            dataset_id=body["dataset_id"],
            revision=body["revision"],
            kind=kind,
            cases=cases,
        )
    except KeyError as exc:
        raise ValueError("benchmark dataset is missing a required field") from exc


__all__ = [
    "BenchmarkDatasetKind",
    "EventBenchmarkCase",
    "EventBenchmarkDataset",
    "EventBenchmarkEvaluator",
    "EventBenchmarkPrediction",
    "EventBenchmarkReport",
    "parse_event_benchmark_dataset",
]
