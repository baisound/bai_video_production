"""TASK-051 R7 packaged acceptance launcher."""
from __future__ import annotations

import os
from pathlib import Path
import sys

from ai_video_production.dbd_training_studio import main


if os.environ.get("BAI_TRAINING_STUDIO_SMOKE_EXIT") == "1":
    # Force packaged JSON Schema resources, PyAV and the real Windows Tk render
    # path to load. Import-only smoke previously missed package-data and Tk
    # delivery/render failures that appeared only during Human Acceptance.
    from jsonschema_specifications import REGISTRY
    import av
    import faster_whisper
    import tkinter as tk

    from ai_video_production.dbd_training_diagnostics import get_diagnostic_logger

    if len(REGISTRY) == 0:
        raise RuntimeError("jsonschema specification registry is empty")
    if not getattr(av, "__version__", None):
        raise RuntimeError("PyAV runtime is unavailable")
    silero_asset = (
        Path(faster_whisper.__file__).resolve().parent
        / "assets" / "silero_vad_v6.onnx"
    )
    if not silero_asset.is_file():
        raise RuntimeError(f"faster-whisper VAD asset is missing: {silero_asset}")

    diagnostics = get_diagnostic_logger()
    if not diagnostics.enabled:
        raise RuntimeError("packaged diagnostics marker was not detected")

    root = tk.Tk()
    root.withdraw()
    try:
        pgm = b"P5\n2 2\n255\n" + bytes((0, 85, 170, 255))
        photo = tk.PhotoImage(data=pgm)
        label = tk.Label(root, image=photo)
        label.pack()
        root.update_idletasks()
        if photo.width() != 2 or photo.height() != 2:
            raise RuntimeError("packaged Tk PGM render smoke returned wrong geometry")
        diagnostics.emit(
            "PACKAGED_TK_SMOKE_PASS",
            image_width=photo.width(),
            image_height=photo.height(),
            executable=Path(sys.executable).name,
        )
    finally:
        root.destroy()
        diagnostics.close(join_timeout=2.0)
    raise SystemExit(0)

raise SystemExit(main())
