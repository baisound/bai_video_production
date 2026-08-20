from pathlib import Path

from ai_video_production.dbd_safe_visual_learning import TrainingDataReviewService
from ai_video_production.dbd_training_workspace import (
    VisualTrainingDomain,
    VisualTrainingManifest,
    VisualTrainingSample,
)

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "src" / "ai_video_production" / "dbd_training_studio.py"
PLAYER = ROOT / "src" / "ai_video_production" / "dbd_training_video_player.py"
UI_HELPERS = ROOT / "src" / "ai_video_production" / "dbd_training_ui_components.py"


def test_r7i_workflow_tabs_and_shared_media_contract_are_canonicalized():
    studio = STUDIO.read_text(encoding="utf-8")
    player = PLAYER.read_text(encoding="utf-8")

    assert 'notebook.add(video_tab, text="動画から一括学習")' in studio
    assert 'notebook.add(visual_tab, text="画像学習データ")' in studio
    for token in (
        'visual_notebook.add(visual_video_tab, text="動画から登録")',
        'visual_notebook.add(visual_manual_tab, text="手動で登録")',
        'visual_notebook.add(visual_list_tab, text="登録済み一覧")',
        'ocr_notebook.add(ocr_video_tab, text="動画から抽出")',
        'ocr_notebook.add(ocr_manual_tab, text="手動で登録")',
        'ocr_notebook.add(ocr_list_tab, text="登録済み一覧")',
        'trivia_notebook.add(mining_tab, text="動画から候補を作る")',
        'trivia_notebook.add(manual_tab, text="手動で登録")',
        'trivia_notebook.add(list_tab, text="登録済み・候補一覧")',
    ):
        assert token in studio

    assert studio.count("TkTrainingMediaPlayer(") == 5
    assert studio.count("TkTrainingMediaSession(") == 1
    assert "TkTrainingVideoPlayer(" not in studio
    assert "TkTrainingVideoSession(" not in studio
    assert "TkTrainingVideoPlayer = TkTrainingMediaPlayer" in player
    assert "TkTrainingVideoSession = TkTrainingMediaSession" in player


def test_media_layout_reserves_height_and_never_uses_form_overflow_to_crop_video():
    studio = STUDIO.read_text(encoding="utf-8")
    player = PLAYER.read_text(encoding="utf-8")
    helpers = UI_HELPERS.read_text(encoding="utf-8")

    assert studio.count("bind_media_minimum_height(") >= 5
    assert 'minimum_fraction=0.55' in studio  # HUD gets a stronger media floor.
    assert "minimum_fraction: float = 0.5" in helpers
    assert 'fit_mode="FIT_TO_VIEW"' in player
    assert "raw_photo.subsample" in player
    assert 'background="black"' in player
    assert "crop(" not in player
    assert "refit_calibration_preview" in studio
    assert 'calibration_canvas.bind("<Configure>", refit_calibration_preview' in studio


def test_image_notification_and_trivia_lists_edit_in_modals():
    studio = STUDIO.read_text(encoding="utf-8")
    for token in (
        'modal.title("画像学習データを編集")',
        'modal.title("右上通知を編集")',
        'modal.title("実況・豆知識を編集")',
        'open_game_element_selector(',
    ):
        assert token in studio
    assert "既存画像から直接登録（補助）" not in studio
    assert "動画から切り出して登録（推奨）" not in studio


def test_visual_training_registration_model_preserves_origin_and_source_metadata(tmp_path):
    manifest = VisualTrainingManifest(tmp_path / "visual.csv")
    image = tmp_path / "perk.pgm"
    image.write_bytes(b"P5\n1 1\n255\n\x00")
    original = VisualTrainingSample(
        domain=VisualTrainingDomain.PERK_ICON,
        label="perk_windows",
        image_path=str(image),
        group="normal",
        source_ref="video://match#frame=120&roi=perk_slot_0",
        notes="note",
        registration_origin="VIDEO_SINGLE",
        slot="perk_slot_0",
        display_state="VISIBLE",
        source_video="match.mp4",
        source_frame=120,
    )
    assert manifest.append(original) is True

    service = TrainingDataReviewService(manifest)
    assert service.relabel_exact(
        image_path=str(image), old_label="perk_windows", new_label="perk_windows_v2"
    ) is True
    current = manifest.list()[0]
    assert current.label == "perk_windows_v2"
    assert current.registration_origin == "VIDEO_SINGLE"
    assert current.slot == "perk_slot_0"
    assert current.display_state == "VISIBLE"
    assert current.source_video == "match.mp4"
    assert current.source_frame == 120


def test_video_batch_learning_uses_range_and_total_sample_bound():
    studio = STUDIO.read_text(encoding="utf-8")
    safe = (ROOT / "src" / "ai_video_production" / "dbd_safe_visual_learning.py").read_text(encoding="utf-8")
    assert "preview_video_batch(" in studio
    assert 'end_frame_exclusive=end_frame' in studio
    assert 'frame_step=frame_step' in studio
    assert 'max_samples=max_samples' in studio
    assert "requested = len(frames) * len(targets)" in safe
    assert 'registration_origin="VIDEO_BATCH"' in safe
