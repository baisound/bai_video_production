"""End-to-end DbD analysis package for editing/NLE handoff."""
from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .game_event_store import GameIntelligenceStore
from .dbd_editing_intelligence import DbDEditingIntelligenceBuilder
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd); temp = Path(raw)
    try:
        temp.write_bytes(data); os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _frame_to_ms(frame: int, num: int, den: int) -> int:
    return round(frame * den * 1000 / num)


class DbDVideoEditingExportService:
    def export(
        self,
        *,
        store: GameIntelligenceStore,
        match_id: str,
        destination: str | Path,
        highlight_threshold: int = 60,
        include_low_confidence: bool = True,
    ) -> dict[str, Path]:
        root = Path(destination)
        if root.exists() and root.is_symlink():
            raise ValueError("export destination must not be symlink")
        root.mkdir(parents=True, exist_ok=True)
        match = store.get_match(match_id)
        events = store.list_events(match_id, latest_only=True)
        plan = DbDEditingIntelligenceBuilder(highlight_threshold=highlight_threshold).build(match, events)
        candidates = tuple(x for x in plan.candidates if include_low_confidence or not x.human_review_required)

        analysis = {
            "schema_version": "1.0.0",
            "match": match.to_dict(),
            "events": [e.to_dict() for e in events],
            "editing_plan": {**plan.to_dict(), "candidates": [x.to_dict() for x in candidates]},
            "production_timeline_mutated": False,
            "resolve_write_performed": False,
            "generated_at": utc_now_iso(),
        }
        analysis["analysis_package_sha256"] = sha256_bytes(canonical_json_bytes(analysis))
        files = {
            "analysis": root / "dbd-analysis.json",
            "edit_plan": root / "edit-candidates.json",
            "markers_csv": root / "markers.csv",
            "events_csv": root / "events.csv",
            "bai_handoff": root / "bai-video-production-handoff.json",
            "manifest": root / "manifest.json",
        }
        _atomic(files["analysis"], canonical_json_bytes(analysis) + b"\n")
        _atomic(files["edit_plan"], canonical_json_bytes({**plan.to_dict(), "candidates": [x.to_dict() for x in candidates]}) + b"\n")
        handoff = {
            "schema_version": "1.0.0",
            "handoff_type": "BAI_VIDEO_PRODUCTION_EDITING_INTELLIGENCE",
            "match_id": match_id,
            "source_rate": {"numerator": match.source_rate.numerator, "denominator": match.source_rate.denominator},
            "markers": [x.to_dict() for x in candidates],
            "production_timeline_mutated": False,
            "human_approval_required": True,
            "generated_at": utc_now_iso(),
        }
        _atomic(files["bai_handoff"], canonical_json_bytes(handoff) + b"\n")

        marker_buf = io.StringIO(newline="")
        w = csv.writer(marker_buf, lineterminator="\n")
        w.writerow(["time_ms", "frame", "duration_frames", "name", "color", "highlight_score", "confidence", "review_required"])
        for item in candidates:
            w.writerow([
                _frame_to_ms(item.source_start_frame, match.source_rate.numerator, match.source_rate.denominator),
                item.source_start_frame,
                item.source_end_frame_exclusive - item.source_start_frame,
                item.label_ja,
                item.marker_color,
                item.highlight_score,
                f"{item.confidence_milli/1000:.3f}",
                "YES" if item.human_review_required else "NO",
            ])
        _atomic(files["markers_csv"], marker_buf.getvalue().encode("utf-8-sig"))

        event_buf = io.StringIO(newline="")
        w = csv.writer(event_buf, lineterminator="\n")
        w.writerow(["event_id", "event_type", "start_frame", "end_frame", "confidence", "confirmation", "review"])
        for event in events:
            w.writerow([event.event_id, event.event_type.value, event.source_range.start_frame, event.source_range.end_frame_exclusive, event.confidence_milli, event.confirmation_state.value, event.review_status.value])
        _atomic(files["events_csv"], event_buf.getvalue().encode("utf-8-sig"))

        manifest = {
            "schema_version": "1.0.0",
            "package_type": "BAI_DBD_EDITING_INTELLIGENCE",
            "match_id": match_id,
            "analysis_revision": match.analysis_revision,
            "files": {key: value.name for key, value in files.items() if key != "manifest"},
            "recommended_consumers": ["BAI_VIDEO_PRODUCTION", "DAVINCI_RESOLVE_MARKERS", "PREMIERE_FCPXML_ADAPTER", "CSV", "JSON"],
            "generated_at": utc_now_iso(),
        }
        manifest["manifest_sha256"] = sha256_bytes(canonical_json_bytes(manifest))
        _atomic(files["manifest"], canonical_json_bytes(manifest) + b"\n")
        return files


__all__ = ["DbDVideoEditingExportService"]
