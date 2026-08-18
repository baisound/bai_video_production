from __future__ import annotations

import argparse
from pathlib import Path

from ai_video_production.dbd_native_pilot import (
    BoundedFrameSamplingPolicy,
    FFmpegPNGFrameSource,
    run_native_media_preflight,
)
from ai_video_production.game_intelligence_gold_io import read_human_gold_dataset
from ai_video_production.serialization import canonical_json_bytes
from ai_video_production.timebase import FrameRate


def main() -> int:
    parser = argparse.ArgumentParser(description="TASK-049 R10B real-media exact-frame preflight")
    parser.add_argument("--video", required=True)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--frame-rate", required=True, help="exact rational rate, e.g. 30000/1001")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-frames-per-case", type=int, default=5)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()

    destination = Path(args.output)
    if destination.exists():
        raise FileExistsError("preflight output already exists")
    if destination.is_symlink():
        raise ValueError("preflight output symlinks are not admitted")
    dataset = read_human_gold_dataset(args.gold)
    report = run_native_media_preflight(
        analysis_video_path=Path(args.video),
        source_rate=FrameRate.parse(args.frame_rate),
        dataset=dataset,
        frame_source=FFmpegPNGFrameSource(args.ffmpeg),
        sampling_policy=BoundedFrameSamplingPolicy(args.max_frames_per_case),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical_json_bytes(report.to_dict()) + b"\n")
    payload = report.to_dict()
    print(f"dataset_sha256={payload['dataset_sha256']}")
    print(f"case_count={len(payload['cases'])}")
    print(f"preflight_report_sha256={payload['preflight_report_sha256']}")
    print("accuracy_measured=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
