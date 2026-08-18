# TASK-049 R10B5A — DbD Training Studio Implementation Report

Date: 2026-08-18
Development depth: DEV-2 STANDARD
Result: IMPLEMENTED / LOCAL TEST PASS / WINDOWS PACKAGED EXECUTION NOT_EXECUTED

## Purpose

Provide one normal GUI/EXE entrypoint for DbD-specific teacher-data and knowledge intake so users do not need to prepare every training input through CLI commands or hand-edited CSV.

## Implemented surfaces

`BAI DbD Training Studio.exe` now supports:

- Visual teacher data:
  - one still sample;
  - CSV with one row or many rows;
  - direct video exact-frame ROI extraction and registration;
  - bulk video labeled ranges through CSV;
  - Survivor HUD / Perk slot / calibrated Killer-Power domains;
  - visual-state group preservation;
  - reference-index build.
- Upper-right OCR:
  - one vocabulary phrase;
  - CSV one/many;
  - direct video OCR scan;
  - Human-selected candidate admission only;
  - vocabulary JSON build.
- Commentary Trivia:
  - one manual item;
  - CSV one/many;
  - existing canonical TranscriptManifest mining;
  - direct owned/permitted video -> local FasterWhisper -> Transcript -> CANDIDATE mining;
  - model download disabled by default.
- Local workspace:
  - video slice artifacts;
  - OCR slice artifacts;
  - transcript/SRT artifacts;
  - visual/OCR manifests;
  - Trivia SQLite;
  - output indexes.

## Video-learning safety boundary

Direct video learning does not invent labels. Human-selected label + exact frame range + target ROI is required for visual registration.

OCR scan does not mutate the OCR vocabulary until the Human selects candidate strings.

Video/Transcript Trivia mining always creates CANDIDATE records and never auto-verifies them.

Killer/Power video learning fails closed unless a calibrated ROI profile defines `killer_power_hud`.

## Data integrity

Visual and OCR CSV manifests now use process-local re-entrant locks and atomic replace writes so background video/OCR jobs cannot leave partially-written manifests during normal GUI operation.

## Packaging

Added:

- `build-dbd-training-studio-exe.bat`
- `packaging/task049_training_studio.spec`
- `packaging/task049_training_studio_windows_entry.py`
- console entrypoint `ai-video-dbd-training-studio`

Expected Windows one-dir output:

`builds\\BAI DbD Training Studio\\BAI DbD Training Studio.exe`

Actual Windows PyInstaller execution is NOT_EXECUTED on the current Linux host and therefore is not reported as PASS.

## Documentation

README links to:

- Training Studio EXE build;
- Training Studio usage;
- recognition accuracy/training;
- slice dataset workflow.

The usage guide explicitly covers single-row CSV, multi-row CSV and direct video learning.

## Verification

Verification after implementation:

- focused Training Studio/workspace/recognition/docs checks: 35 PASS;
- all current repository `tests/test_*.py`: 2116 PASS / 1 Windows-only SKIP / 0 FAIL / 0 DESELECT;
- `python -m compileall -q src`: PASS;
- `git diff --check`: PASS before commit/package.

The single skip is the existing TASK-047 Inno Setup acceptance gate and is unrelated to this slice.
