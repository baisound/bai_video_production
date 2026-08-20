from pathlib import Path
import subprocess

from ai_video_production.dbd_hud_detectors import TesseractCliOcrEngine

ROOT = Path(__file__).resolve().parents[1]


def test_shared_media_preview_uses_runtime_viewport_bounds():
    player = (ROOT / "src/ai_video_production/dbd_training_video_player.py").read_text(encoding="utf-8")
    decoder = (ROOT / "src/ai_video_production/dbd_persistent_video_preview.py").read_text(encoding="utf-8")
    studio = (ROOT / "src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    assert "def set_preview_bounds" in player
    assert "VIDEO_PREVIEW_BOUNDS_CHANGED" in player
    assert "self.root.after(120, self._apply_viewport_bounds)" in player
    assert "schedule_calibration_decoder_fit" in studio
    assert 'calibration_canvas.bind("<Configure>", schedule_calibration_decoder_fit' in studio
    assert "self._decoder_reset_requested = True" in decoder
    assert "maximum_width / source_width" in decoder
    assert "1.0," not in decoder.split("scale = min(", 1)[1].split(")", 1)[0]


def test_training_studio_explains_visual_group_presets():
    studio = (ROOT / "src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    assert 'VISUAL_GROUP_PRESETS = ("normal", "active", "greyed", "hard-negative")' in studio
    assert "通常は normal のままでOK" in studio
    assert "hard-negative=見た目が似るが正解ではない誤認防止画像" in studio
    assert studio.count("values=VISUAL_GROUP_PRESETS") >= 3


def test_windows_packaging_collects_faster_whisper_assets():
    spec = (ROOT / "packaging/task049_training_studio.spec").read_text(encoding="utf-8")
    runner = (ROOT / "tools/task051/run_task051_r7_acceptance.py").read_text(encoding="utf-8")
    launcher = (ROOT / "tools/task051/task051_training_studio_launcher.py").read_text(encoding="utf-8")
    assert 'collect_data_files("faster_whisper")' in spec
    assert '"--collect-data", "faster_whisper"' in runner
    assert '"silero_vad_v6.onnx"' in launcher
    assert "faster-whisper VAD asset is missing" in launcher


def test_tesseract_hud_ocr_runs_multiple_segmentation_modes(tmp_path, monkeypatch):
    image = tmp_path / "roi.pgm"
    image.write_bytes(b"P5\n2 2\n255\n" + bytes((0, 32, 64, 255)))
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(tuple(cmd))
        psm = cmd[cmd.index("--psm") + 1]
        text = {"7": "アポカリプス\n", "6": "アポカンプス\n", "11": "アポカリプス\n"}[psm]
        return subprocess.CompletedProcess(cmd, 0, stdout=text.encode("utf-8"), stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    engine = TesseractCliOcrEngine("tesseract")
    rows = engine.read_candidates(image, language="jpn+eng")
    assert rows == ("アポカリプス", "アポカンプス")
    assert [call[call.index("--psm") + 1] for call in calls] == ["7", "6", "11"]
    assert engine.read(image, language="jpn+eng") == "アポカリプス"


def test_ocr_scan_uses_higher_resolution_preprocessing():
    workspace = (ROOT / "src/ai_video_production/dbd_training_workspace.py").read_text(encoding="utf-8")
    assert "width=1024" in workspace
    assert "height=512" in workspace
    assert "read_candidates" in workspace
