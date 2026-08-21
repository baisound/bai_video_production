from __future__ import annotations

import csv
from pathlib import Path

import ai_video_production.dbd_training_workspace as training
from ai_video_production.dbd_training_workspace import (
    DbDTrainingWorkspace,
    OcrVocabularySample,
    VisualTrainingDomain,
    VisualVideoTrainingRequest,
)
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment


def _pgm(path: Path, seed: int = 0) -> Path:
    width = height = 8
    pixels = bytes(((index + seed) % 256) for index in range(width * height))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"P5\n{width} {height}\n255\n".encode() + pixels)
    return path


class FakeExtractor:
    def __init__(self, executable: str = "ffmpeg") -> None:
        self.executable = executable

    def extract_frame_roi(self, *, video_path, frame_index, roi, output_path, width=96, height=96):
        return _pgm(Path(output_path), seed=frame_index)

    def normalize_still_to_pgm(self, *, image_path, output_path, width=96, height=96):
        Path(output_path).write_bytes(Path(image_path).read_bytes())
        return Path(output_path)


class FakeOcr:
    def __init__(self, executable: str = "tesseract") -> None:
        self.executable = executable

    def read(self, image_path, *, language="jpn+eng"):
        name = Path(image_path).stem
        if "000000000" in name or "000000060" in name:
            return "追跡 +125"
        return "窓越え"


def test_video_learning_extracts_exact_roi_frames_and_registers_samples(tmp_path, monkeypatch):
    monkeypatch.setattr(training, "FFmpegSliceExtractor", FakeExtractor)
    video = tmp_path / "match.mp4"
    video.write_bytes(b"video")
    workspace = DbDTrainingWorkspace(tmp_path / "workspace")
    request = VisualVideoTrainingRequest(
        domain=VisualTrainingDomain.PERK_ICON,
        label="perk_windows_of_opportunity",
        video_path=str(video),
        start_frame=0,
        end_frame_exclusive=121,
        frame_step=60,
        slot=2,
        group="normal",
    )

    report = workspace.extract_visual_from_video(request)
    assert report.requested_frames == 3
    assert report.extracted == 3
    assert report.registered == 3
    assert report.rejected == 0
    assert report.roi_id == "perk_slot_2"
    rows = workspace.visual.list(domain=VisualTrainingDomain.PERK_ICON)
    assert len(rows) == 3
    assert all("#frame=" in row.source_ref and "roi=perk_slot_2" in row.source_ref for row in rows)
    assert (Path(report.output_directory) / "video-learning-receipt.json").is_file()

    duplicate = workspace.extract_visual_from_video(request)
    assert duplicate.registered == 0
    assert duplicate.duplicates == 3


def test_video_learning_csv_accepts_one_or_many_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(training, "FFmpegSliceExtractor", FakeExtractor)
    video = tmp_path / "match.mp4"
    video.write_bytes(b"video")
    workspace = DbDTrainingWorkspace(tmp_path / "workspace")
    manifest = tmp_path / "ranges.csv"
    with manifest.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "domain", "label", "video_path", "start_frame", "end_frame_exclusive", "frame_step",
            "slot", "group", "source_ref", "notes", "roi_profile_path", "max_samples",
            "match_id", "signal_kind",
        ])
        writer.writeheader()
        writer.writerow({
            "domain": "PERK_ICON", "label": "perk_a", "video_path": str(video), "start_frame": "0",
            "end_frame_exclusive": "61", "frame_step": "60", "slot": "0", "group": "normal", "max_samples": "10",
        })
        writer.writerow({
            "domain": "SURVIVOR_HUD", "label": "INJURED", "video_path": str(video), "start_frame": "100",
            "end_frame_exclusive": "221", "frame_step": "60", "slot": "1", "group": "injured", "max_samples": "10",
            "match_id": "match-owned-1", "signal_kind": "SURVIVOR_STATE",
        })

    report = workspace.import_video_training_csv(manifest)
    assert report.rejected == 0
    assert report.accepted == 5
    assert len(workspace.visual.list()) == 5


def test_video_learning_requires_explicit_killer_power_roi(tmp_path, monkeypatch):
    monkeypatch.setattr(training, "FFmpegSliceExtractor", FakeExtractor)
    video = tmp_path / "match.mp4"
    video.write_bytes(b"video")
    workspace = DbDTrainingWorkspace(tmp_path / "workspace")
    request = VisualVideoTrainingRequest(
        domain=VisualTrainingDomain.KILLER_POWER,
        label="killer_trapper",
        video_path=str(video),
        start_frame=0,
        end_frame_exclusive=2,
        frame_step=1,
        slot=None,
    )
    try:
        workspace.extract_visual_from_video(request)
    except ValueError as exc:
        assert "killer_power_hud" in str(exc)
    else:
        raise AssertionError("KILLER_POWER must fail closed without an explicit ROI")


def test_upper_right_video_ocr_returns_human_review_candidates_only(tmp_path, monkeypatch):
    monkeypatch.setattr(training, "FFmpegSliceExtractor", FakeExtractor)
    monkeypatch.setattr(training, "TesseractCliOcrEngine", FakeOcr)
    video = tmp_path / "match.mp4"
    video.write_bytes(b"video")
    workspace = DbDTrainingWorkspace(tmp_path / "workspace")

    report = workspace.scan_upper_right_ocr_from_video(
        video_path=video,
        start_frame=0,
        end_frame_exclusive=121,
        frame_step=60,
    )
    assert report.scanned == 3
    assert report.rejected == 0
    assert {item.normalized_text for item in report.candidates} == {"追跡 125", "窓越え"}
    assert workspace.ocr.list() == ()  # scan alone never mutates the vocabulary

    selected = report.candidates[0]
    workspace.ocr.append(OcrVocabularySample("CHASE", selected.text, source_ref=Path(selected.image_path).as_uri()))
    assert len(workspace.ocr.list()) == 1


def test_trivia_can_be_mined_from_existing_video_transcript_manifest(tmp_path):
    workspace = DbDTrainingWorkspace(tmp_path / "workspace")
    transcript = TranscriptManifest(
        generate_id(IdKind.ASSET),
        "ja",
        "fixture",
        "fixture-model",
        (
            TranscriptSegment("seg-1", 0, 1_000_000, "ちなみにパークは発動条件を満たす必要があります。"),
            TranscriptSegment("seg-2", 1_000_000, 2_000_000, "普通に走っています。"),
        ),
    )
    source = tmp_path / "transcript.json"
    import json
    source.write_text(json.dumps(transcript.to_dict(), ensure_ascii=False), encoding="utf-8")
    count = workspace.mine_trivia_from_transcript(source)
    assert count == 1
    rows = workspace.trivia.list_latest()
    assert len(rows) == 1
    assert rows[0].status.value == "CANDIDATE"
    assert rows[0].source_ref.startswith("transcript://")


def test_trivia_can_be_mined_directly_from_video_via_local_asr_port(tmp_path, monkeypatch):
    from types import SimpleNamespace

    workspace = DbDTrainingWorkspace(tmp_path / "workspace")
    video = tmp_path / "match.mp4"
    video.write_bytes(b"video")
    transcript = TranscriptManifest(
        generate_id(IdKind.ASSET),
        "ja",
        "fixture",
        "fixture-model",
        (TranscriptSegment("seg-1", 0, 1_000_000, "豆知識ですが、パークには発動条件があります。"),),
    )
    transcript_path = tmp_path / "published-transcript.json"
    subtitle_path = tmp_path / "published.srt"
    transcript_path.write_text("{}", encoding="utf-8")
    subtitle_path.write_text("", encoding="utf-8")

    class FakeProvider:
        def __init__(self, config):
            self.config = config

    class FakeService:
        @staticmethod
        def run(media_path, output_directory, *, provider, source_asset_id=None, language=None, timeline_rate=None):
            return SimpleNamespace(transcript=transcript, transcript_path=transcript_path, subtitle_path=subtitle_path)

    monkeypatch.setattr(training, "FasterWhisperProvider", FakeProvider)
    monkeypatch.setattr(training, "LocalTranscriptionService", FakeService)
    report = workspace.mine_trivia_from_video(video_path=video, model="small", language="ja")
    assert report.mined_candidates == 1
    assert report.source_asset_id == transcript.source_asset_id
    assert workspace.trivia.list_latest()[0].status.value == "CANDIDATE"


def test_video_learning_supports_item_and_addon_rois(tmp_path, monkeypatch):
    import json
    from ai_video_production.dbd_vision_slices import DBDHudRoiProfile, NormalizedROI
    monkeypatch.setattr(training, "FFmpegSliceExtractor", FakeExtractor)
    video = tmp_path / "match.mp4"
    video.write_bytes(b"video")
    profile = DBDHudRoiProfile(
        profile_id="loadout",
        lower_left_loadout_hud=NormalizedROI("lower_left_loadout_hud", 0.13, 0.74, 0.20, 0.24),
        item_slot=NormalizedROI("item_slot", 0.14, 0.80, 0.08, 0.12),
        addon_slots=(
            NormalizedROI("addon_slot_0", 0.225, 0.80, 0.045, 0.055),
            NormalizedROI("addon_slot_1", 0.275, 0.80, 0.045, 0.055),
        ),
    )
    profile_path = tmp_path / "roi.json"
    profile_path.write_text(json.dumps(profile.to_dict()), encoding="utf-8")
    workspace = DbDTrainingWorkspace(tmp_path / "workspace")
    item_report = workspace.extract_visual_from_video(VisualVideoTrainingRequest(
        domain=VisualTrainingDomain.ITEM_ICON, label="item_medkit", video_path=str(video),
        start_frame=0, end_frame_exclusive=2, frame_step=1, roi_profile_path=str(profile_path),
    ))
    addon_report = workspace.extract_visual_from_video(VisualVideoTrainingRequest(
        domain=VisualTrainingDomain.ADDON_ICON, label="addon_bandages", video_path=str(video),
        start_frame=0, end_frame_exclusive=2, frame_step=1, slot=1, roi_profile_path=str(profile_path),
    ))
    assert item_report.roi_id == "item_slot"
    assert addon_report.roi_id == "addon_slot_1"
    assert len(workspace.visual.list(domain=VisualTrainingDomain.ITEM_ICON)) == 2
    assert len(workspace.visual.list(domain=VisualTrainingDomain.ADDON_ICON)) == 2
