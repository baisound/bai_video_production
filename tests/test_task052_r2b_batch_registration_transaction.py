from __future__ import annotations

import json
from pathlib import Path
import threading

import pytest

from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_safe_visual_learning import SafeVisualLearningService
from ai_video_production.dbd_training_workspace import VisualTrainingDomain, VisualTrainingManifest
from ai_video_production.dbd_vision_slices import FFmpegSliceExtractor, NormalizedROI


class Extractor:
    ffmpeg_executable = "fake-ffmpeg"

    def extract_frame_roi(self, **kwargs):
        output = Path(kwargs["output_path"])
        output.write_bytes(b"P5\n2 2\n255\n\x00\x01\x02\x03")
        return output


def service_and_video(tmp_path: Path):
    video = tmp_path / "owned.mp4"
    video.write_bytes(b"owned-video")
    manifest = VisualTrainingManifest(tmp_path / "visual.csv")
    service = SafeVisualLearningService(workspace_root=tmp_path, manifest=manifest)
    service.extractor = Extractor()
    return service, manifest, video


def staged(service, video: Path, frame: int):
    return service.preview_video_frame(
        domain=VisualTrainingDomain.PERK_ICON, label="perk_a",
        visibility=HudVisibility.VISIBLE, video_path=video, frame_index=frame,
        roi=NormalizedROI("perk_slot_0", 0.0, 0.0, 0.1, 0.1),
        registration_origin="VIDEO_BATCH",
    )


def test_confirm_batch_writes_manifest_once_and_rebuilds_once(tmp_path: Path) -> None:
    service, manifest, video = service_and_video(tmp_path)
    values = (staged(service, video, 1), staged(service, video, 2))
    writes = 0
    original_write = manifest._write

    def counted(rows):
        nonlocal writes
        writes += 1
        return original_write(rows)

    manifest._write = counted
    progress = []
    report = service.confirm_batch(
        values, progress=progress.append, extract_seconds=1.25,
        stage_subprocess_count=2,
    )
    assert writes == 1
    assert report.confirm_count == 2 and report.duplicate_count == 0
    assert report.subprocess_count == 2
    assert report.extract_seconds == 1.25
    assert report.affected_domains == ("PERK_ICON",)
    assert len(report.index_paths) == 1 and Path(report.index_paths[0]).is_file()
    assert len(manifest.list()) == 2
    assert {item.phase for item in progress} == {"PREPARE", "COMMIT", "INDEX_REBUILD"}
    receipts = tuple((tmp_path / "staging" / "visual-learning" / "batches").glob("*.json"))
    payload = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert payload["stage_count"] == 2 and payload["confirm_count"] == 2


def test_cancel_before_commit_preserves_preview_and_manifest(tmp_path: Path) -> None:
    service, manifest, video = service_and_video(tmp_path)
    value = staged(service, video, 1)
    event = threading.Event()
    event.set()
    report = service.confirm_batch((value,), cancel_event=event)
    assert report.cancelled is True and report.confirm_count == 0
    assert manifest.list() == ()
    assert service.load_staged(value.staging_id).state.value == "PREVIEWED"
    assert not tuple((tmp_path / "training-data").rglob("*.pgm"))


def test_preview_cancel_is_bounded_and_marks_partial_staging_discarded(tmp_path: Path) -> None:
    service, manifest, video = service_and_video(tmp_path)
    event = threading.Event()

    def progress(item):
        if item.processed == 1:
            event.set()

    from ai_video_production.dbd_safe_visual_learning import BatchVisualTarget
    report = service.preview_video_batch(
        video_path=video, start_frame=0, end_frame_exclusive=3, frame_step=1,
        targets=(BatchVisualTarget(
            VisualTrainingDomain.PERK_ICON, "perk_a", HudVisibility.VISIBLE,
            NormalizedROI("perk_slot_0", 0.0, 0.0, 0.1, 0.1),
        ),),
        progress=progress, cancel_event=event,
    )
    assert report.cancelled is True
    assert report.stage_count == 1 and report.subprocess_count == 1
    assert report.staged == () and manifest.list() == ()


def test_manifest_failure_rolls_back_committed_files(tmp_path: Path) -> None:
    service, manifest, video = service_and_video(tmp_path)
    value = staged(service, video, 1)

    def fail(_rows):
        raise OSError("manifest unavailable")

    manifest._write = fail
    with pytest.raises(OSError, match="manifest unavailable"):
        service.confirm_batch((value,), rebuild_indexes=False)
    assert not tuple((tmp_path / "training-data").rglob("*.pgm"))
    assert service.load_staged(value.staging_id).state.value == "PREVIEWED"


def test_ffmpeg_extractor_passes_shared_no_console_kwargs(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "owned.mp4"
    source.write_bytes(b"video")
    target = tmp_path / "out.pgm"
    seen = {}

    def fake_run(_cmd, **kwargs):
        seen.update(kwargs)
        target.write_bytes(b"P5\n1 1\n255\n\x00")
        return type("Completed", (), {"returncode": 0})()

    import ai_video_production.dbd_vision_slices as slices
    monkeypatch.setattr(slices, "_no_console_subprocess_kwargs", lambda: {"creationflags": 0x08000000})
    monkeypatch.setattr(slices.subprocess, "run", fake_run)
    FFmpegSliceExtractor("ffmpeg").extract_frame_roi(
        video_path=source, frame_index=0,
        roi=NormalizedROI("roi", 0.0, 0.0, 0.5, 0.5), output_path=target,
    )
    assert seen["creationflags"] == 0x08000000


def test_training_studio_uses_background_transaction_progress_and_cancel() -> None:
    text = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    assert "safe_visual_learning.confirm_batch(" in text
    assert "progress_queue=progress_events" in text
    assert "一括処理をキャンセル" in text
    confirm_body = text.split("def confirm_video_learning()", 1)[1].split("def import_video_ranges_csv()", 1)[0]
    assert "confirm_register(" not in confirm_body
