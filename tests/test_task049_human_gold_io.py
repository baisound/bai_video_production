from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.game_intelligence_gold_io import (
    HUMAN_GOLD_CSV_COLUMNS,
    compile_human_gold_csv,
    read_human_gold_dataset,
    write_human_gold_dataset,
)
from ai_video_production.ids import IdKind, generate_id


def write_csv(path: Path, rows: list[str]) -> None:
    path.write_text(",".join(HUMAN_GOLD_CSV_COLUMNS) + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_compile_csv_to_hashed_human_gold_and_round_trip(tmp_path: Path) -> None:
    asset_id = generate_id(IdKind.ASSET)
    csv_path = tmp_path / "gold.csv"
    write_csv(
        csv_path,
        [
            "case-002,200,220,,,,true",
            "case-001,100,130,WINDOW_VAULT,110,115,false",
        ],
    )
    dataset = compile_human_gold_csv(
        csv_path,
        source_asset_id=asset_id,
        dataset_id="dbd-real-pilot",
        revision=1,
        labeler_ref="human://owner-1",
    )
    assert [case.case_id for case in dataset.cases] == ["case-001", "case-002"]
    assert dataset.cases[0].expected_event_type.value == "WINDOW_VAULT"
    assert dataset.cases[1].expected_abstention is True
    output = tmp_path / "gold.json"
    write_human_gold_dataset(output, dataset)
    assert read_human_gold_dataset(output) == dataset
    with pytest.raises(FileExistsError):
        write_human_gold_dataset(output, dataset)


def test_csv_contract_is_strict_and_rejects_label_ambiguity(tmp_path: Path) -> None:
    asset_id = generate_id(IdKind.ASSET)
    bad_header = tmp_path / "bad-header.csv"
    bad_header.write_text("case_id,start,end\ncase-001,1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="header"):
        compile_human_gold_csv(
            bad_header,
            source_asset_id=asset_id,
            dataset_id="gold",
            revision=1,
            labeler_ref="human://owner",
        )

    bad = tmp_path / "bad.csv"
    write_csv(bad, ["case-001,1,20,WINDOW_VAULT,5,7,true"])
    with pytest.raises(ValueError, match="both expected event and expected abstention"):
        compile_human_gold_csv(
            bad,
            source_asset_id=asset_id,
            dataset_id="gold",
            revision=1,
            labeler_ref="human://owner",
        )

    unknown = tmp_path / "unknown.csv"
    write_csv(unknown, ["case-001,1,20,UNKNOWN_EVENT,5,7,false"])
    with pytest.raises(ValueError, match="UNKNOWN_EVENT"):
        compile_human_gold_csv(
            unknown,
            source_asset_id=asset_id,
            dataset_id="gold",
            revision=1,
            labeler_ref="human://owner",
        )
