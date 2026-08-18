#!/usr/bin/env python3
"""Extract exact-frame DbD ROI slices for labeling/training.

The tool supports either explicit normalized ROI coordinates or a calibrated
DBDHudRoiProfile target such as ``survivor:0`` / ``perk:2`` / ``upper-right``.
It can also write a CSV manifest so slice provenance is not lost during manual
labeling.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_video_production.dbd_vision_slices import DBDHudRoiProfile, FFmpegSliceExtractor, NormalizedROI
from ai_video_production.serialization import sha256_bytes


def _profile_roi(profile: DBDHudRoiProfile, target: str) -> NormalizedROI:
    value = target.strip().lower()
    if value.startswith("survivor:"):
        return profile.survivor_slot_roi(int(value.split(":", 1)[1]))
    if value.startswith("perk:"):
        return profile.perk_slot_roi(int(value.split(":", 1)[1]))
    mapping = {
        "upper-right": profile.upper_right_notifications,
        "notifications": profile.upper_right_notifications,
        "lower-left": profile.lower_left_survivor_hud,
        "survivor-hud": profile.lower_left_survivor_hud,
        "bottom-right": profile.bottom_right_perks,
        "perks": profile.bottom_right_perks,
    }
    if value in mapping:
        return mapping[value]
    if value in {"killer-power", "killer_power"}:
        if profile.killer_power_hud is None:
            raise ValueError("ROI profile does not define killer_power_hud")
        return profile.killer_power_hud
    raise ValueError("unknown --target; use survivor:0..3, perk:0..3, upper-right, lower-left, bottom-right, or killer-power")


def _resolve_roi(args: argparse.Namespace) -> NormalizedROI:
    if args.roi_profile or args.target:
        if not args.roi_profile or not args.target:
            raise ValueError("--roi-profile and --target must be used together")
        profile = DBDHudRoiProfile.from_dict(json.loads(Path(args.roi_profile).read_text(encoding="utf-8")))
        return _profile_roi(profile, args.target)
    required = (args.roi_id, args.x, args.y, args.width, args.height)
    if any(value is None for value in required):
        raise ValueError("use either --roi-profile/--target or --roi-id/--x/--y/--width/--height")
    return NormalizedROI(args.roi_id, args.x, args.y, args.width, args.height)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract exact-frame DbD ROI slices for labeling/training")
    parser.add_argument("--video", required=True)
    parser.add_argument("--frames", required=True, help="comma-separated exact frame indices")
    parser.add_argument("--roi-profile", help="calibrated DBDHudRoiProfile JSON")
    parser.add_argument("--target", help="survivor:0..3, perk:0..3, upper-right, lower-left, bottom-right, killer-power")
    parser.add_argument("--roi-id")
    parser.add_argument("--x", type=float)
    parser.add_argument("--y", type=float)
    parser.add_argument("--width", type=float)
    parser.add_argument("--height", type=float)
    parser.add_argument("--slice-width", type=int, default=96)
    parser.add_argument("--slice-height", type=int, default=96)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--manifest", help="optional CSV manifest path; defaults to <output-dir>/slice-manifest.csv")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()

    try:
        roi = _resolve_roi(args)
    except (ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    if args.slice_width < 8 or args.slice_height < 8:
        parser.error("slice dimensions must be >= 8")

    source = Path(args.video)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    extractor = FFmpegSliceExtractor(args.ffmpeg)
    try:
        frames = [int(item.strip()) for item in args.frames.split(",") if item.strip()]
    except ValueError:
        parser.error("--frames must contain integer frame indices")
    if not frames or any(frame < 0 for frame in frames):
        parser.error("--frames must contain one or more non-negative frame indices")

    rows: list[dict[str, object]] = []
    for frame in frames:
        target = output / f"{roi.roi_id}_f{frame:09d}.pgm"
        extractor.extract_frame_roi(
            video_path=source,
            frame_index=frame,
            roi=roi,
            output_path=target,
            width=args.slice_width,
            height=args.slice_height,
        )
        digest = sha256_bytes(target.read_bytes())
        rows.append({
            "label": "",
            "image_path": str(target.resolve()),
            "group": "",
            "source_video": str(source.resolve()),
            "frame_index": frame,
            "roi_id": roi.roi_id,
            "slice_sha256": digest,
        })
        print(target)

    manifest = Path(args.manifest) if args.manifest else output / "slice-manifest.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, str]] = []
    if manifest.is_file():
        with manifest.open(encoding="utf-8-sig", newline="") as handle:
            existing = list(csv.DictReader(handle))
    fieldnames = ["label", "image_path", "group", "source_video", "frame_index", "roi_id", "slice_sha256"]
    with manifest.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in existing + rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    print(f"[PASS] manifest={manifest} slices={len(rows)} roi={roi.roi_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
