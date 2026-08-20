# TASK-051 R7M — Shared Media Runtime / OCR / Image Group Usability Hardening

## Status

`IMPLEMENTED / WINDOWS_HUMAN_ACCEPTANCE_PENDING`

## Problem statement

R7I-R7L Human Acceptance exposed four remaining cross-cutting defects:

1. Shared Media containers are large but decoded previews are capped at 720x405, leaving most of the viewport black and making HUD/OCR inspection unnecessarily small.
2. The packaged executable imports FasterWhisper but omits `faster_whisper/assets/silero_vad_v6.onnx`, causing VAD transcription to fail with ONNXRuntime `NO_SUCHFILE`.
3. `画像グループ` is a free-text field with no operator guidance even though the model already uses visual-state provenance groups.
4. Upper-right OCR uses one 512x256 crop and one `--psm 6` Tesseract pass, which is fragile for small Japanese HUD text.

## Design

### Dynamic Fit-to-View

All five Shared Media surfaces use the actual Tk viewport as the decoder output bound. Resize events are debounced for 120ms. The existing decoder-thread ownership is preserved: UI code only marks the worker decoder for replacement, and the worker reopens PyAV on the next request.

The output bound is clamped to 1920x1080 for predictable CPU/memory cost. PyAV may upscale a lower-resolution source so the preview uses the available annotation viewport. Aspect ratio is preserved and source pixels are never cropped.

HUD calibration binds the same viewport-bound update to its custom Canvas so ROI overlays and the visible frame remain one geometry contract.

### FasterWhisper packaged assets

The Windows PyInstaller spec and R7 packaged acceptance command collect FasterWhisper package data. Packaged smoke verifies that `assets/silero_vad_v6.onnx` exists before PASS.

### Image Group operator contract

The UI exposes four recommended provenance groups while keeping the Combobox editable for backwards compatibility/custom groups:

- `normal`: normal/default visual state. Use this unless another state is intentionally being learned.
- `active`: activated/highlighted state.
- `greyed`: disabled/grey visual state.
- `hard-negative`: visually similar but explicitly not the correct class; used to reduce false positives.

The same guidance appears in batch learning, video-single registration and manual-image registration.

### OCR improvement

The upper-right ROI is normalized to 1024x512 before OCR. Tesseract runs deterministic multi-pass recognition in PSM order `7, 6, 11` (single-line, compact block, sparse text). Unique alternatives are surfaced as human-review candidates rather than silently claiming one uncertain string as truth. Manual correction remains the canonical acceptance step.

## Safety boundaries

- No OCR candidate is automatically promoted to verified truth.
- No fuzzy substitution silently rewrites player names or unknown text.
- Existing custom image-group strings remain readable/editable.
- Runtime model download policy is unchanged.
- The media viewport change does not change exact Crop/OCR evidence coordinates; exact extraction still uses source-frame contracts.
