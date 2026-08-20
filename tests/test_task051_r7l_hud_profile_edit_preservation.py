from pathlib import Path

from ai_video_production.dbd_hud_calibration_editor import RoiPixelEditor
from ai_video_production.dbd_vision_slices import NormalizedROI


def test_loaded_profile_rebase_preserves_unselected_rois_and_new_reset_baseline():
    defaults = {
        "perk_slot_0": NormalizedROI("perk_slot_0", 0.10, 0.10, 0.10, 0.10),
        "perk_slot_1": NormalizedROI("perk_slot_1", 0.30, 0.10, 0.10, 0.10),
    }
    editor = RoiPixelEditor(source_width=1000, source_height=1000, rois=defaults)
    editor.move("perk_slot_0", dx_px=25)

    loaded = {
        "perk_slot_0": NormalizedROI("perk_slot_0", 0.55, 0.60, 0.08, 0.08),
        "perk_slot_1": NormalizedROI("perk_slot_1", 0.70, 0.60, 0.08, 0.08),
    }
    editor.rebase(loaded)

    assert editor.undo() is None
    other_before = editor.rois["perk_slot_1"]
    editor.move("perk_slot_0", dx_px=10)
    assert editor.rois["perk_slot_1"] == other_before

    editor.reset("perk_slot_0")
    assert editor.rois["perk_slot_0"] == loaded["perk_slot_0"]
    assert editor.rois["perk_slot_1"] == loaded["perk_slot_1"]


def test_registered_hud_load_rebases_attached_editor_before_any_adjustment():
    source = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    start = source.index("def load_calibration_profile()")
    end = source.index("def test_profile_resolution_and_anchor()", start)
    block = source[start:end]
    assert 'loaded_rois = rois_from_profile(profile)' in block
    assert 'editor.rebase(loaded_rois)' in block
    assert 'calibration_state["editor"] = RoiPixelEditor(' in block
    assert 'refresh_roi_xywh()' in block
