"""TASK-050 R2 pixel-precise DbD HUD calibration contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .dbd_vision_slices import NormalizedROI


class HeartbeatTrend(str, Enum):
    RISING = "RISING"
    STABLE = "STABLE"
    FALLING = "FALLING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class PixelRect:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0 or self.width < 1 or self.height < 1:
            raise ValueError("pixel ROI must have non-negative origin and positive size")

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass(frozen=True, slots=True)
class RoiEditSnapshot:
    roi_id: str
    before: NormalizedROI
    after: NormalizedROI


@dataclass(frozen=True, slots=True)
class HeartbeatObservation:
    frame_index: int
    active: bool | None
    intensity_milli: int | None
    trend: HeartbeatTrend
    confidence_milli: int
    roi_id: str = "heartbeat_hud"

    def __post_init__(self) -> None:
        if self.frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        if self.intensity_milli is not None and not 0 <= self.intensity_milli <= 1000:
            raise ValueError("intensity_milli must be 0..1000")
        if not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")


def infer_heartbeat_trend(values: tuple[int, ...], *, deadband_milli: int = 60) -> HeartbeatTrend:
    if len(values) < 2:
        return HeartbeatTrend.UNKNOWN
    if any(value < 0 or value > 1000 for value in values):
        raise ValueError("heartbeat intensity values must be 0..1000")
    delta = values[-1] - values[0]
    if abs(delta) <= deadband_milli:
        return HeartbeatTrend.STABLE
    return HeartbeatTrend.RISING if delta > 0 else HeartbeatTrend.FALLING


class RoiPixelEditor:
    """Edit normalized ROIs through exact source-frame pixels.

    Parent/child relationships are informational only: moving a parent never
    silently moves or rescales its children.
    """

    def __init__(self, *, source_width: int, source_height: int, rois: Mapping[str, NormalizedROI]) -> None:
        if source_width < 64 or source_height < 64:
            raise ValueError("source geometry is invalid")
        self.source_width = source_width
        self.source_height = source_height
        self._initial = dict(rois)
        self._rois = dict(rois)
        self._undo: list[RoiEditSnapshot] = []
        self._redo: list[RoiEditSnapshot] = []

    @property
    def rois(self) -> dict[str, NormalizedROI]:
        return dict(self._rois)

    def rebase(self, rois: Mapping[str, NormalizedROI]) -> None:
        """Make a loaded HUD profile the new edit-session baseline.

        A profile load must replace all editable ROIs atomically. History from
        the previously displayed profile is discarded so editing/resetting one
        ROI cannot restore stale/default positions for the others.
        """
        self._initial = dict(rois)
        self._rois = dict(rois)
        self._undo.clear()
        self._redo.clear()

    def normalized_to_pixels(self, roi: NormalizedROI) -> PixelRect:
        x = round(roi.x * self.source_width)
        y = round(roi.y * self.source_height)
        right = round((roi.x + roi.width) * self.source_width)
        bottom = round((roi.y + roi.height) * self.source_height)
        x = max(0, min(x, self.source_width - 1))
        y = max(0, min(y, self.source_height - 1))
        right = max(x + 1, min(right, self.source_width))
        bottom = max(y + 1, min(bottom, self.source_height))
        return PixelRect(x, y, right - x, bottom - y)

    def pixels_to_normalized(self, roi_id: str, rect: PixelRect) -> NormalizedROI:
        if rect.right > self.source_width or rect.bottom > self.source_height:
            raise ValueError("pixel ROI must stay inside source frame")
        return NormalizedROI(
            roi_id,
            rect.x / self.source_width,
            rect.y / self.source_height,
            rect.width / self.source_width,
            rect.height / self.source_height,
        )

    def pixel_rect(self, roi_id: str) -> PixelRect:
        return self.normalized_to_pixels(self._require(roi_id))

    def set_pixel_rect(self, roi_id: str, rect: PixelRect) -> NormalizedROI:
        before = self._require(roi_id)
        after = self.pixels_to_normalized(roi_id, rect)
        return self._commit(roi_id, before, after)

    def move(self, roi_id: str, *, dx_px: int = 0, dy_px: int = 0) -> NormalizedROI:
        rect = self.pixel_rect(roi_id)
        x = min(max(0, rect.x + dx_px), self.source_width - rect.width)
        y = min(max(0, rect.y + dy_px), self.source_height - rect.height)
        return self.set_pixel_rect(roi_id, PixelRect(x, y, rect.width, rect.height))

    def adjust_edges(self, roi_id: str, *, left_delta_px: int = 0, top_delta_px: int = 0, right_delta_px: int = 0, bottom_delta_px: int = 0) -> NormalizedROI:
        rect = self.pixel_rect(roi_id)
        left = min(max(0, rect.x + left_delta_px), self.source_width - 1)
        top = min(max(0, rect.y + top_delta_px), self.source_height - 1)
        right = min(max(left + 1, rect.right + right_delta_px), self.source_width)
        bottom = min(max(top + 1, rect.bottom + bottom_delta_px), self.source_height)
        return self.set_pixel_rect(roi_id, PixelRect(left, top, right-left, bottom-top))

    def undo(self) -> NormalizedROI | None:
        if not self._undo:
            return None
        edit = self._undo.pop()
        self._rois[edit.roi_id] = edit.before
        self._redo.append(edit)
        return edit.before

    def redo(self) -> NormalizedROI | None:
        if not self._redo:
            return None
        edit = self._redo.pop()
        self._rois[edit.roi_id] = edit.after
        self._undo.append(edit)
        return edit.after

    def reset(self, roi_id: str) -> NormalizedROI:
        before = self._require(roi_id)
        return self._commit(roi_id, before, self._initial[roi_id])

    def add_or_replace(self, roi: NormalizedROI) -> None:
        before = self._rois.get(roi.roi_id, roi)
        self._rois[roi.roi_id] = roi
        self._initial.setdefault(roi.roi_id, before)
        self._undo.append(RoiEditSnapshot(roi.roi_id, before, roi))
        self._redo.clear()

    def _require(self, roi_id: str) -> NormalizedROI:
        if roi_id not in self._rois:
            raise KeyError(f"ROI is not calibrated: {roi_id}")
        return self._rois[roi_id]

    def _commit(self, roi_id: str, before: NormalizedROI, after: NormalizedROI) -> NormalizedROI:
        if before == after:
            return before
        self._rois[roi_id] = after
        self._undo.append(RoiEditSnapshot(roi_id, before, after))
        self._redo.clear()
        return after


ROI_DISPLAY_JA = {
    "lower_left_survivor_hud": "左下：生存者状態 全体",
    "survivor_slot_0": "生存者1",
    "survivor_slot_1": "生存者2",
    "survivor_slot_2": "生存者3",
    "survivor_slot_3": "生存者4",
    "lower_left_loadout_hud": "左下：アイテム・アドオン 全体",
    "item_slot": "アイテム",
    "addon_slot_0": "アドオン1",
    "addon_slot_1": "アドオン2",
    "upper_right_notifications": "右上：通知",
    "bottom_right_perks": "右下：パーク 全体",
    "perk_slot_0": "パーク1（上向き）",
    "perk_slot_1": "パーク2（右向き）",
    "perk_slot_2": "パーク3（下向き）",
    "perk_slot_3": "パーク4（左向き）",
    "heartbeat_hud": "サバイバー：心臓鼓動表示",
    "killer_power_hud": "キラー能力表示エリア（任意）",
}
