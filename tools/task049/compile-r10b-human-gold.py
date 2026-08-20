from __future__ import annotations

import argparse
from pathlib import Path

from ai_video_production.game_intelligence_gold_io import (
    compile_human_gold_csv,
    write_human_gold_dataset,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile TASK-049 R10B Human Gold CSV into canonical JSON")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--source-asset-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--revision", type=int, default=1)
    parser.add_argument("--labeler-ref", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    dataset = compile_human_gold_csv(
        args.csv,
        source_asset_id=args.source_asset_id,
        dataset_id=args.dataset_id,
        revision=args.revision,
        labeler_ref=args.labeler_ref,
    )
    write_human_gold_dataset(Path(args.output), dataset, overwrite=args.overwrite)
    payload = dataset.to_dict()
    print(f"dataset_id={dataset.dataset_id}")
    print(f"revision={dataset.revision}")
    print(f"case_count={len(dataset.cases)}")
    print(f"dataset_sha256={payload['dataset_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
