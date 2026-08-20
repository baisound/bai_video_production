"""User-facing DbD video analysis -> editing-information package.

The workspace combines local ASR and the trained upper-right OCR vocabulary.
Canonical Game Event Timeline exports remain additive when an existing Game
Intelligence store is supplied; this module never invents canonical events.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .dbd_hud_detectors import normalize_hud_text
from .dbd_training_workspace import DbDTrainingWorkspace
from .cut_candidates import load_transcript_manifest
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


@dataclass(frozen=True, slots=True)
class VideoProbe:
    fps_num: int
    fps_den: int
    duration_ms: int
    frame_count: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class EditingFinding:
    finding_id: str
    kind: str
    start_ms: int
    end_ms: int
    label: str
    text: str
    confidence_milli: int
    highlight_score: int
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "kind": self.kind,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "label": self.label,
            "text": self.text,
            "confidence_milli": self.confidence_milli,
            "highlight_score": self.highlight_score,
            "source": self.source,
        }


class DbDVideoAnalysisWorkspaceService:
    def __init__(
        self,
        workspace: DbDTrainingWorkspace,
        *,
        ffprobe_executable: str = "ffprobe",
        ffmpeg_executable: str = "ffmpeg",
        tesseract_executable: str = "tesseract",
        model_cache: str | Path | None = None,
    ) -> None:
        self.workspace = workspace
        self.ffprobe_executable = ffprobe_executable
        self.ffmpeg_executable = ffmpeg_executable
        self.tesseract_executable = tesseract_executable
        self.model_cache = model_cache

    def probe(self, video_path: str | Path) -> VideoProbe:
        path = Path(video_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError("解析動画が見つかりません。")
        argv = [
            self.ffprobe_executable, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,avg_frame_rate,nb_frames,duration",
            "-of", "json", str(path),
        ]
        try:
            proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
        except FileNotFoundError as exc:
            raise ValueError("ffprobeが見つかりません。実行環境設定を確認してください。") from exc
        if proc.returncode != 0:
            raise ValueError("動画情報を取得できませんでした。")
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        stream = (data.get("streams") or [{}])[0]
        rate = str(stream.get("avg_frame_rate") or "30/1")
        try:
            num, den = (int(x) for x in rate.split("/", 1))
            if num <= 0 or den <= 0: raise ValueError
        except Exception:
            num, den = 30, 1
        duration_s = float(stream.get("duration") or 0.0)
        frame_count = int(stream.get("nb_frames") or 0)
        if frame_count <= 0 and duration_s > 0:
            frame_count = max(1, round(duration_s * num / den))
        duration_ms = max(0, round(duration_s * 1000))
        return VideoProbe(num, den, duration_ms, frame_count, int(stream.get("width") or 0), int(stream.get("height") or 0))

    @staticmethod
    def _speech_score(text: str) -> int:
        score = 35
        score += min(25, len(text) // 4)
        if any(ch in text for ch in "!?！？"):
            score += 15
        if any(term in text for term in ("すご", "やば", "ナイス", "チェイス", "神", "うま", "危な")):
            score += 15
        return max(0, min(100, score))

    def analyze(
        self,
        *,
        video_path: str | Path,
        destination: str | Path,
        model: str = "small",
        device: str = "auto",
        compute_type: str = "int8",
        language: str = "ja",
        allow_model_download: bool = False,
        ocr_interval_seconds: float = 2.0,
        max_ocr_samples: int = 300,
    ) -> dict[str, Any]:
        source = Path(video_path).expanduser().resolve()
        probe = self.probe(source)
        root = Path(destination).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        findings: list[EditingFinding] = []

        transcription = self.workspace.mine_trivia_from_video(
            video_path=source,
            model=model,
            device=device,
            compute_type=compute_type,
            language=language or None,
            allow_model_download=allow_model_download,
            cache_directory=self.model_cache,
        )
        transcript = load_transcript_manifest(transcription.transcript_path)
        for index, seg in enumerate(transcript.segments, 1):
            start_ms = seg.start_us // 1000
            end_ms = max(start_ms + 1, seg.end_us // 1000)
            findings.append(EditingFinding(
                finding_id=f"speech-{index:06d}", kind="SPEECH", start_ms=start_ms, end_ms=end_ms,
                label="発言", text=seg.text, confidence_milli=800,
                highlight_score=self._speech_score(seg.text), source="FasterWhisper",
            ))

        interval_frames = max(1, round(float(ocr_interval_seconds) * probe.fps_num / probe.fps_den))
        ocr_report = None
        if probe.frame_count > 0:
            effective_step = interval_frames
            estimated = (probe.frame_count + effective_step - 1) // effective_step
            if estimated > max_ocr_samples:
                effective_step = max(effective_step, (probe.frame_count + max_ocr_samples - 1) // max_ocr_samples)
            ocr_report = self.workspace.scan_upper_right_ocr_from_video(
                video_path=source,
                start_frame=0,
                end_frame_exclusive=probe.frame_count,
                frame_step=effective_step,
                ffmpeg_executable=self.ffmpeg_executable,
                tesseract_executable=self.tesseract_executable,
                max_samples=max_ocr_samples,
            )
            vocabulary = tuple(self.workspace.ocr.list())
            for index, cand in enumerate(ocr_report.candidates, 1):
                normalized = normalize_hud_text(cand.text)
                signal = "右上通知"
                confidence = 600
                for sample in vocabulary:
                    if normalize_hud_text(sample.phrase) == normalized:
                        signal = sample.signal_id
                        confidence = 900
                        break
                start_ms = round(cand.frame_index * probe.fps_den * 1000 / probe.fps_num)
                findings.append(EditingFinding(
                    finding_id=f"ocr-{index:06d}", kind="HUD_NOTIFICATION", start_ms=start_ms,
                    end_ms=start_ms + 1200, label=signal, text=cand.text,
                    confidence_milli=confidence, highlight_score=70 if confidence >= 800 else 50,
                    source="Tesseract/UpperRightROI",
                ))

        findings.sort(key=lambda x: (x.start_ms, x.kind, x.finding_id))
        payload = {
            "schema_version": "1.0.0",
            "package_type": "BAI_DBD_VIDEO_ANALYSIS",
            "source_video_name": source.name,
            "source_video_sha256": sha256_bytes(source.read_bytes()) if source.stat().st_size <= 64 * 1024 * 1024 else "not-computed-large-file",
            "video_probe": probe.__dict__ if hasattr(probe, "__dict__") else {
                "fps_num": probe.fps_num, "fps_den": probe.fps_den, "duration_ms": probe.duration_ms,
                "frame_count": probe.frame_count, "width": probe.width, "height": probe.height,
            },
            "findings": [x.to_dict() for x in findings],
            "transcript_path": str(transcription.transcript_path),
            "subtitle_path": str(transcription.subtitle_path),
            "ocr": None if ocr_report is None else {
                "requested_frames": ocr_report.requested_frames,
                "scanned": ocr_report.scanned,
                "candidate_count": len(ocr_report.candidates),
                "rejected": ocr_report.rejected,
                "errors": list(ocr_report.errors),
            },
            "canonical_game_event_timeline_generated": False,
            "canonical_note": "CGEL events are not invented from weak OCR/ASR. Existing canonical event analysis can be exported separately.",
            "generated_at": utc_now_iso(),
        }
        (root / "analysis.json").write_bytes(canonical_json_bytes(payload) + b"\n")
        handoff = {
            "schema_version": "1.0.0",
            "handoff_type": "BAI_VIDEO_PRODUCTION_EDITING_INTELLIGENCE",
            "source_video_name": source.name,
            "source_rate": {"numerator": probe.fps_num, "denominator": probe.fps_den},
            "duration_ms": probe.duration_ms,
            "markers": [x.to_dict() for x in findings],
            "suggested_clips": [
                {
                    "finding_id": x.finding_id,
                    "source_in_ms": max(0, x.start_ms - (2000 if x.highlight_score >= 60 else 0)),
                    "source_out_ms": min(probe.duration_ms or x.end_ms + 3000, x.end_ms + (3000 if x.highlight_score >= 60 else 0)),
                    "reason": x.label,
                    "highlight_score": x.highlight_score,
                    "human_review_required": x.confidence_milli < 800,
                }
                for x in findings if x.highlight_score >= 60
            ],
            "production_timeline_mutated": False,
            "contract_note": "Import as reviewable source analysis; Human approval precedes production timeline adoption.",
            "generated_at": utc_now_iso(),
        }
        (root / "bai-video-production-handoff.json").write_bytes(canonical_json_bytes(handoff) + b"\n")
        marker_buf = io.StringIO(newline="")
        writer = csv.writer(marker_buf, lineterminator="\n")
        writer.writerow(["start_ms", "end_ms", "kind", "label", "text", "confidence", "highlight_score", "source"])
        for row in findings:
            writer.writerow([row.start_ms, row.end_ms, row.kind, row.label, row.text, row.confidence_milli, row.highlight_score, row.source])
        (root / "editing-markers.csv").write_text(marker_buf.getvalue(), encoding="utf-8-sig")
        if Path(transcription.subtitle_path).is_file():
            shutil.copy2(transcription.subtitle_path, root / "transcript.srt")
        manifest = {
            "schema_version": "1.0.0", "package_type": "BAI_DBD_EDITING_INTELLIGENCE",
            "files": ["analysis.json", "bai-video-production-handoff.json", "editing-markers.csv", "transcript.srt"],
            "finding_count": len(findings),
            "speech_count": sum(1 for x in findings if x.kind == "SPEECH"),
            "notification_count": sum(1 for x in findings if x.kind == "HUD_NOTIFICATION"),
            "recommended_next": "BAI VIDEO PRODUCTION / NLE marker import",
            "generated_at": utc_now_iso(),
        }
        (root / "manifest.json").write_bytes(canonical_json_bytes(manifest) + b"\n")
        return {"root": str(root), "manifest": manifest, "analysis": payload}


__all__ = ["VideoProbe", "EditingFinding", "DbDVideoAnalysisWorkspaceService"]
