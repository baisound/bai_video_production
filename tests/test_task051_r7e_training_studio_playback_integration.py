from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "src" / "ai_video_production" / "dbd_training_studio.py"
TRANSPORT = ROOT / "src" / "ai_video_production" / "dbd_video_transport.py"
PREVIEW = ROOT / "src" / "ai_video_production" / "dbd_persistent_video_preview.py"
SHARED = ROOT / "src" / "ai_video_production" / "dbd_training_video_player.py"


def test_hud_calibration_uses_shared_persistent_in_memory_preview_pipeline():
    studio = STUDIO.read_text(encoding="utf-8")
    shared = SHARED.read_text(encoding="utf-8")
    assert "calibration_video_session = TkTrainingMediaSession(" in studio
    assert "apply_calibration_memory_preview" in studio
    assert "calibration_video_session.request_frame(frame_index)" in studio
    assert "PersistentPreviewWorker" in shared
    assert 'PhotoImage(data=frame.tk_photo_data())' in shared
    assert '"preview_image": GrayImage(' in studio
    # Continuous preview must no longer create a frame-specific PGM file for
    # every playback tick in any user-facing video surface.
    assert 'f"transport-{frame_index:09d}.pgm"' not in studio


def test_transport_uses_monotonic_clock_instead_of_callback_counting():
    transport = TRANSPORT.read_text(encoding="utf-8")
    assert "import time" in transport
    assert "playback_frame_for_elapsed" in transport
    assert "elapsed=self.clock()-self._clock_anchor_time" in transport
    assert "elapsed_seconds=elapsed" in transport
    assert "maximum_preview_fps=30.0" in transport


def test_preview_worker_contract_is_bounded_latest_request_wins():
    preview = PREVIEW.read_text(encoding="utf-8")
    assert "OrderedDict" in preview
    assert "ring_size: int = 24" in preview
    assert "self._pending = request" in preview
    assert "if not stale:" in preview
    assert "and not newer" not in preview
    assert "request.generation != self._generation" in preview
