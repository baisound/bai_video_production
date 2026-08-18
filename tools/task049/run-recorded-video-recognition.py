#!/usr/bin/env python3
"""Run the TASK-049 deterministic recorded-video HUD recognition baseline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_video_production.dbd_hud_detectors import DBDNotificationTextDetector, PerkIconDetector, SurvivorHudStateDetector, TesseractCliOcrEngine
from ai_video_production.dbd_killer_knowledge import KillerPowerVisualRecognizer
from ai_video_production.dbd_recorded_video_recognition import DbDRecordedVideoRecognizer
from ai_video_production.dbd_vision_slices import DBDHudRoiProfile, ReferenceSliceIndex


def _snapshot(value):
    return {
        "frame_index": value.frame_index,
        "survivor_slots": [{"slot": x.slot, "state": x.state.value, "confidence_milli": x.confidence_milli} for x in value.survivor_slots],
        "perk_slots": [{"slot": x.slot, "perk_id": x.perk_id, "confidence_milli": x.confidence_milli, "top_k": [{"label": c.label, "confidence_milli": c.confidence_milli} for c in x.candidates]} for x in value.perk_slots],
        "notification": None if value.notification is None else {"text": value.notification.text, "signal_id": value.notification.signal_id, "confidence_milli": value.notification.confidence_milli},
        "killer_power": None if value.killer_power is None else {"entity_id": value.killer_power.entity_id, "kind": None if value.killer_power.kind is None else value.killer_power.kind.value, "confidence_milli": value.killer_power.confidence_milli},
        "slice_artifacts": [{"roi_id": x.roi_id, "sha256": x.sha256} for x in value.slice_artifacts],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DbD lower-left HUD / upper-right OCR / bottom-right perk recognition baseline")
    parser.add_argument("--video", required=True)
    parser.add_argument("--frames", required=True, help="Two comma-separated exact frame indices, e.g. 1200,1203")
    parser.add_argument("--survivor-index")
    parser.add_argument("--perk-index")
    parser.add_argument("--killer-power-index")
    parser.add_argument("--roi-profile", help="Optional DBDHudRoiProfile JSON")
    parser.add_argument("--tesseract", default="tesseract")
    parser.add_argument("--notification-vocabulary", help="Optional Training Studio vocabulary JSON")
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    frames = tuple(int(x.strip()) for x in args.frames.split(",") if x.strip())
    if len(frames) != 2 or frames[1] <= frames[0]:
        parser.error("--frames requires exactly two ascending exact frame indices")
    profile = DBDHudRoiProfile()
    if args.roi_profile:
        profile = DBDHudRoiProfile.from_dict(json.loads(Path(args.roi_profile).read_text(encoding="utf-8")))
    survivor = SurvivorHudStateDetector(ReferenceSliceIndex.load(args.survivor_index)) if args.survivor_index else None
    perk = PerkIconDetector(ReferenceSliceIndex.load(args.perk_index)) if args.perk_index else None
    killer = KillerPowerVisualRecognizer(ReferenceSliceIndex.load(args.killer_power_index)) if args.killer_power_index else None
    if args.no_ocr:
        ocr = None
    elif args.notification_vocabulary:
        ocr = DBDNotificationTextDetector.from_vocabulary_file(TesseractCliOcrEngine(args.tesseract), args.notification_vocabulary)
    else:
        ocr = DBDNotificationTextDetector(TesseractCliOcrEngine(args.tesseract))
    recognizer = DbDRecordedVideoRecognizer(roi_profile=profile, survivor_detector=survivor, perk_detector=perk, notification_detector=ocr, killer_power_recognizer=killer)
    before = recognizer.recognize_frame(video_path=args.video, frame_index=frames[0])
    after = recognizer.recognize_frame(video_path=args.video, frame_index=frames[1])
    observations = recognizer.event_observations(before, after)
    decision = recognizer.fuse_frame_pair(before, after)
    body = {
        "schema_version": "1.0.0",
        "video": str(Path(args.video)),
        "roi_profile": profile.to_dict(),
        "frames": [_snapshot(before), _snapshot(after)],
        "event_observations": [{"event_type": x.event_type.value, "modality": x.modality.value, "confidence_milli": x.confidence_milli, "source_range": x.source_range.to_dict(), "evidence_ref": x.evidence_ref} for x in observations],
        "fusion": {"event_type": None if decision.event_type is None else decision.event_type.value, "confidence_milli": decision.confidence_milli, "reason_codes": list(decision.reason_codes), "modalities": [x.value for x in decision.modalities]},
        "production_accuracy_claim_authorized": False,
    }
    target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
