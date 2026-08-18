"""TASK-049 R10B Human-Gold authoring/import helpers.

Human labels are authored outside detector code and compiled into the same
hashed EventBenchmarkDataset contract consumed by R10B.  The compiler never
passes expected labels to a detector.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Mapping

from .canonical_game_event import GameEventType
from .game_event_evidence import SourceFrameRange
from .game_intelligence_benchmark import (
    BenchmarkDatasetKind,
    EventBenchmarkCase,
    EventBenchmarkDataset,
    parse_event_benchmark_dataset,
)
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes


HUMAN_GOLD_CSV_COLUMNS = (
    "case_id",
    "evaluation_start_frame",
    "evaluation_end_frame_exclusive",
    "expected_event_type",
    "expected_start_frame",
    "expected_end_frame_exclusive",
    "expected_abstention",
)


def _int_field(row: Mapping[str, str], name: str, *, required: bool) -> int | None:
    raw = row.get(name, "").strip()
    if not raw:
        if required:
            raise ValueError(f"{name} is required")
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
    return value


def _bool_field(row: Mapping[str, str], name: str) -> bool:
    raw = row.get(name, "").strip().lower()
    if raw == "true":
        return True
    if raw == "false":
        return False
    raise ValueError(f"{name} must be true or false")


def compile_human_gold_rows(
    rows: Iterable[Mapping[str, str]],
    *,
    source_asset_id: str,
    dataset_id: str,
    revision: int,
    labeler_ref: str,
) -> EventBenchmarkDataset:
    validate_id(source_asset_id, IdKind.ASSET)
    if not isinstance(labeler_ref, str) or not labeler_ref.strip() or len(labeler_ref) > 256 or "\x00" in labeler_ref:
        raise ValueError("labeler_ref must be a bounded non-empty provenance reference")

    cases: list[EventBenchmarkCase] = []
    for row_number, row in enumerate(rows, start=2):
        unknown = set(row) - set(HUMAN_GOLD_CSV_COLUMNS)
        if unknown:
            raise ValueError(f"row {row_number} contains unknown columns: {sorted(unknown)}")
        case_id = row.get("case_id", "").strip()
        evaluation_start = _int_field(row, "evaluation_start_frame", required=True)
        evaluation_end = _int_field(row, "evaluation_end_frame_exclusive", required=True)
        assert evaluation_start is not None and evaluation_end is not None
        evaluation_range = SourceFrameRange(evaluation_start, evaluation_end)
        expected_abstention = _bool_field(row, "expected_abstention")
        raw_event = row.get("expected_event_type", "").strip()
        if raw_event:
            try:
                expected_event = GameEventType(raw_event)
            except ValueError as exc:
                raise ValueError(f"row {row_number} has unsupported expected_event_type") from exc
            if expected_event is GameEventType.UNKNOWN_EVENT:
                raise ValueError("Human Gold UNKNOWN_EVENT must be represented as an abstention/negative case")
            expected_start = _int_field(row, "expected_start_frame", required=True)
            expected_end = _int_field(row, "expected_end_frame_exclusive", required=True)
            assert expected_start is not None and expected_end is not None
            expected_range = SourceFrameRange(expected_start, expected_end)
        else:
            expected_event = None
            expected_range = None
            if row.get("expected_start_frame", "").strip() or row.get("expected_end_frame_exclusive", "").strip():
                raise ValueError(f"row {row_number} cannot define expected event frames without expected_event_type")
        if expected_abstention and expected_event is not None:
            raise ValueError(f"row {row_number} cannot be both expected event and expected abstention")
        cases.append(
            EventBenchmarkCase(
                case_id=case_id,
                source_ref=source_asset_id,
                expected_event_type=expected_event,
                expected_range=expected_range,
                expected_abstention=expected_abstention,
                labeler_ref=labeler_ref,
                evaluation_range=evaluation_range,
            )
        )
    cases.sort(key=lambda item: item.case_id)
    return EventBenchmarkDataset(
        dataset_id=dataset_id,
        revision=revision,
        kind=BenchmarkDatasetKind.HUMAN_GOLD,
        cases=tuple(cases),
    )


def compile_human_gold_csv(
    path: str | Path,
    *,
    source_asset_id: str,
    dataset_id: str,
    revision: int,
    labeler_ref: str,
) -> EventBenchmarkDataset:
    source = Path(path)
    if not source.exists() or not source.is_file():
        raise ValueError("CSV path must be an existing file")
    if source.is_symlink():
        raise ValueError("CSV symlinks are not admitted")
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != HUMAN_GOLD_CSV_COLUMNS:
            raise ValueError("CSV header must exactly match the TASK-049 Human Gold contract")
        return compile_human_gold_rows(
            reader,
            source_asset_id=source_asset_id,
            dataset_id=dataset_id,
            revision=revision,
            labeler_ref=labeler_ref,
        )


def write_human_gold_dataset(path: str | Path, dataset: EventBenchmarkDataset, *, overwrite: bool = False) -> None:
    if dataset.kind is not BenchmarkDatasetKind.HUMAN_GOLD:
        raise ValueError("only HUMAN_GOLD datasets may be written by this helper")
    destination = Path(path)
    if destination.exists() and not overwrite:
        raise FileExistsError("Human Gold output already exists")
    if destination.exists() and destination.is_symlink():
        raise ValueError("Human Gold output symlinks are not admitted")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical_json_bytes(dataset.to_dict()) + b"\n")


def read_human_gold_dataset(path: str | Path) -> EventBenchmarkDataset:
    source = Path(path)
    if not source.exists() or not source.is_file() or source.is_symlink():
        raise ValueError("Human Gold JSON path must be a regular existing file")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Human Gold JSON is invalid") from exc
    dataset = parse_event_benchmark_dataset(payload, require_hash=True)
    if dataset.kind is not BenchmarkDatasetKind.HUMAN_GOLD:
        raise ValueError("dataset is not HUMAN_GOLD")
    return dataset


__all__ = [
    "HUMAN_GOLD_CSV_COLUMNS",
    "compile_human_gold_csv",
    "compile_human_gold_rows",
    "read_human_gold_dataset",
    "write_human_gold_dataset",
]
