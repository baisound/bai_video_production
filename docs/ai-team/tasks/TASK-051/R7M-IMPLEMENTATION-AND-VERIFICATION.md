# TASK-051 R7M — Implementation and Verification

## Implemented

- dynamic Shared Media decoder bounds from the real Tk viewport;
- debounced worker-thread decoder reconfiguration;
- HUD Canvas uses the same dynamic preview bounds;
- PyAV preview scaling can upscale low-resolution sources while preserving aspect ratio;
- FasterWhisper package data included in normal and R7 PyInstaller builds;
- packaged smoke verifies `silero_vad_v6.onnx`;
- guided image-group presets/help added to batch, video-single and manual registration;
- upper-right OCR extraction raised to 1024x512;
- Tesseract PSM 7/6/11 multi-pass candidate generation;
- regression tests for all four findings.

## Verification

- TASK-049/050/051: `335 PASS / 1 display-only SKIP` in the available Linux test runtime.
- R7M focused: `5 / 5 PASS`.
- `py_compile`: PASS.
- `git diff --check`: PASS.
- Full repository run reaches the known pre-existing README local-link failure at `docs/design/TASK-006_SUBTITLE-WORKSPACE_詳細設計_Ver1.0.md`; no R7M-specific full-suite failure was observed before that existing blocker.

Windows packaged build and Human Acceptance remain required for dynamic viewport sizing, FasterWhisper VAD asset loading and real Tesseract quality.
