from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ai_video_production.dbd_notification_semantics import (
    KNOWN_SIGNAL_JA,
    notification_signal_choices,
    notification_signal_label,
)
from ai_video_production.dbd_training_studio_foundation import resolve_workspace_runtime_profile
from ai_video_production.dbd_video_transport import VideoTransportMetadata, VideoTransportModel

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "src" / "ai_video_production" / "dbd_training_studio.py"
PLAYER = ROOT / "src" / "ai_video_production" / "dbd_training_video_player.py"
TRANSPORT = ROOT / "src" / "ai_video_production" / "dbd_video_transport.py"
REVIEW = ROOT / "src" / "ai_video_production" / "dbd_training_review_ui_v2.py"
FOUNDATION_UI = ROOT / "src" / "ai_video_production" / "dbd_training_studio_foundation_ui.py"
WORKSPACE = ROOT / "src" / "ai_video_production" / "dbd_training_workspace.py"
ASR = ROOT / "src" / "ai_video_production" / "faster_whisper_asr.py"


def test_notification_signal_choices_expose_more_than_chase_and_keep_known_labels():
    values = dict(notification_signal_choices(()))
    assert values["チェイス関連通知"] == "CHASE"
    assert values["負傷関連通知"] == "INJURY"
    assert values["フック関連通知"] == "HOOK"
    assert values["脱出関連通知"] == "ESCAPE"
    assert values["その他・システム通知"] == "SYSTEM"
    assert len(KNOWN_SIGNAL_JA) >= 10
    assert notification_signal_label("DOWN") == "ダウン関連通知"


def test_selected_runtime_profile_is_not_silently_ignored():
    selected = object()

    class Store:
        def __init__(self):
            self.loaded = []
            self.auto_calls = 0

        def load(self, profile_id):
            self.loaded.append(profile_id)
            return selected

        def autodetect(self):
            self.auto_calls += 1
            return object()

    store = Store()
    workspace = SimpleNamespace(selected_runtime_profile_id="default")
    assert resolve_workspace_runtime_profile(workspace, store=store) is selected
    assert store.loaded == ["default"]
    assert store.auto_calls == 0


def test_time_seek_bar_and_exact_transport_model_contract():
    source = TRANSPORT.read_text(encoding="utf-8")
    assert 'text="タイムシーク"' in source
    assert 'action="seek_bar"' in source
    assert "self.seek_scale=ttk.Scale" in source

    metadata = VideoTransportMetadata(30, 1, 100.0, 3000)
    model = VideoTransportModel(metadata)
    model.set_frame(round(metadata.last_frame * 0.75))
    assert 74.9 <= model.position_seconds() <= 75.1


def test_hud_preview_updates_image_in_place_and_auto_correction_is_backgrounded():
    studio = STUDIO.read_text(encoding="utf-8")
    assert 'calibration_canvas.itemconfigure(preview_item, image=photo)' in studio
    assert 'calibration_canvas.delete("all")' not in studio
    assert 'run_background("HUD自動補正テスト", execute_alignment, completed)' in studio
    assert 'calibration_tab.update_idletasks()' not in studio


def test_ambiguous_hud_profiles_are_user_disambiguated_without_silent_selection():
    studio = STUDIO.read_text(encoding="utf-8")
    assert "ERR_DBD_HUD_PROFILE_AMBIGUOUS" in studio
    assert "choose_hud_profile_candidate" in studio
    assert "resolve_workflow_hud_profile" in studio
    assert "HUD_PROFILE_DISAMBIGUATED" in studio
    # Batch / single-image / OCR routes all use the same bounded resolver.
    assert studio.count("resolve_workflow_hud_profile(") >= 4


def test_standard_media_surfaces_reserve_more_space_and_runtime_ffprobe_is_reused():
    studio = STUDIO.read_text(encoding="utf-8")
    player = PLAYER.read_text(encoding="utf-8")
    assert "minimum_fraction=0.6, minimum_pixels=420" in studio
    assert "minimum_fraction=0.55, minimum_pixels=400" in studio
    assert studio.count("ffprobe_executable=runtime_ffprobe") >= 4
    assert "def set_preview_bounds" in player
    assert "VIDEO_PREVIEW_BOUNDS_CHANGED" in player
    assert "self.frame.columnconfigure(0, weight=2)" in player


def test_review_surface_refreshes_from_canonical_stores_on_navigation():
    review = REVIEW.read_text(encoding="utf-8")
    foundation = FOUNDATION_UI.read_text(encoding="utf-8")
    assert 'return refresh_all' in review
    assert 'review_notebook.bind("<<NotebookTabChanged>>"' in review
    assert 'notebook.bind("<<NotebookTabChanged>>", refresh_review_when_selected' in foundation
    assert 'NotificationSemanticStore(' in review
    assert 'notification_signal_label(item.signal_id)' in review
    assert "Human Goldは、人が別工程で正解確認・修正した外部教師データ/Evidence" in review


def test_runtime_tool_paths_and_asr_cache_are_propagated_to_learning_operations():
    studio = STUDIO.read_text(encoding="utf-8")
    workspace = WORKSPACE.read_text(encoding="utf-8")
    assert 'runtime_tesseract = active_runtime.tesseract.effective_path or "tesseract"' in studio
    assert 'cache_directory=runtime_model_cache' in studio
    assert 'cache_directory: str | Path | None = None' in workspace
    assert 'cache_directory=cache_directory' in workspace
    assert 'cause_message=(str(cause)[:500] if cause is not None else None)' in studio


def test_operation_failures_are_written_to_opt_in_diagnostics():
    studio = STUDIO.read_text(encoding="utf-8")
    assert '"TRAINING_OPERATION_FAILED"' in studio
    assert '"BACKGROUND_OPERATION_FAILED"' in studio
    assert "product_error_details" in studio
