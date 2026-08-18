from ai_video_production.dbd_hud_calibration_editor import HeartbeatTrend, PixelRect, RoiPixelEditor, infer_heartbeat_trend
from ai_video_production.dbd_vision_slices import NormalizedROI


def test_move_one_pixel_round_trip():
    roi = NormalizedROI("perk_slot_0", 0.5, 0.5, 0.1, 0.1)
    editor = RoiPixelEditor(source_width=1920, source_height=1080, rois={roi.roi_id: roi})
    before = editor.pixel_rect("perk_slot_0")
    editor.move("perk_slot_0", dx_px=1)
    after = editor.pixel_rect("perk_slot_0")
    assert after.x == before.x + 1
    assert after.y == before.y


def test_adjust_edges_and_history():
    roi = NormalizedROI("heartbeat_hud", 0.2, 0.2, 0.2, 0.2)
    editor = RoiPixelEditor(source_width=1000, source_height=1000, rois={roi.roi_id: roi})
    before = editor.pixel_rect("heartbeat_hud")
    editor.adjust_edges("heartbeat_hud", left_delta_px=-1, right_delta_px=2)
    changed = editor.pixel_rect("heartbeat_hud")
    assert changed.x == before.x - 1
    assert changed.right == before.right + 2
    editor.undo()
    assert editor.pixel_rect("heartbeat_hud") == before
    editor.redo()
    assert editor.pixel_rect("heartbeat_hud") == changed


def test_parent_move_does_not_move_child():
    parent = NormalizedROI("bottom_right_perks", 0.7, 0.6, 0.3, 0.4)
    child = NormalizedROI("perk_slot_0", 0.8, 0.7, 0.05, 0.08)
    editor = RoiPixelEditor(source_width=1920, source_height=1080, rois={parent.roi_id: parent, child.roi_id: child})
    child_before = editor.pixel_rect("perk_slot_0")
    editor.move("bottom_right_perks", dx_px=-5)
    assert editor.pixel_rect("perk_slot_0") == child_before


def test_direct_xywh_rejects_out_of_bounds():
    roi = NormalizedROI("heartbeat_hud", 0.1, 0.1, 0.1, 0.1)
    editor = RoiPixelEditor(source_width=1920, source_height=1080, rois={roi.roi_id: roi})
    try:
        editor.set_pixel_rect("heartbeat_hud", PixelRect(1900, 100, 50, 50))
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-bounds ROI must fail")


def test_heartbeat_trend():
    assert infer_heartbeat_trend((100, 160, 250)) is HeartbeatTrend.RISING
    assert infer_heartbeat_trend((900, 700, 400)) is HeartbeatTrend.FALLING
    assert infer_heartbeat_trend((500, 510, 520)) is HeartbeatTrend.STABLE
    assert infer_heartbeat_trend((500,)) is HeartbeatTrend.UNKNOWN
