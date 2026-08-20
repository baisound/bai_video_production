"""Safe initialization helper for optional HUD ROIs."""
from __future__ import annotations

from .dbd_hud_calibration_editor import PixelRect, RoiPixelEditor


def ensure_optional_roi_initialized(
    editor: RoiPixelEditor,
    roi_id: str,
) -> bool:
    """Create a neutral centered placeholder only when the ROI is absent."""
    if roi_id in editor.rois:
        return False

    width = max(80, min(320, editor.source_width // 6))
    height = max(60, min(220, editor.source_height // 6))
    x = max(0, (editor.source_width - width) // 2)
    y = max(0, (editor.source_height - height) // 2)
    normalized = editor.pixels_to_normalized(
        roi_id,
        PixelRect(x, y, width, height),
    )
    editor.add_or_replace(normalized)
    return True
