# TASK-049 Development Handoff — 2026-08-18

- R10B5B — HUD Calibration / ROI Profile + Data Migration: Training Studio video/still preview drag ROI registration; normalized coordinates; frame/UI/game-version/profile-version metadata; anchor clip persistence; fail-closed automatic profile resolution; bounded +/- pixel anchor translation applied to child slots; recorded-video recognizer integration; checksum migration Backup/Preview/Restore with automatic pre-restore safety backup.

## Current result

`R10B1-R10B5A RECOGNITION / LLM / TRIVIA / TRAINING-STUDIO LOCAL PASS / WINDOWS PACKAGE + REAL-MEDIA HUMAN-GOLD GATES REMAIN`

Branch: `feature/task-049-dbd-game-intelligence`

TASK-009 remains `R0 IMPLEMENTED / AUTOMATED VALIDATED` and was not repurposed as CGEL ownership.

## Implemented

- R1 — CGEL Match / Event / Evidence / Review / Knowledge-ref contracts and exact timebase
- R2 — append-only SQLite Game Intelligence store, revision/resume/checkpoint integrity
- R3 — existing BVP Asset/Normalization/ASR/Timebase adapters
- R4 — bounded deterministic DbD Event producer/resolver with UNKNOWN/NEEDS_REVIEW
- R5 — patch-aware/source-provenanced Perk Knowledge baseline with LIVE/PTB separation
- R6A — append-only Human Review backend/read model
- R6B — additive V6 Game Intelligence Human Review Workspace
- R7 — Commentary Planner / typed deterministic Fact Validator / candidate store
- R8A — proposal-only GameEventToProductionBridge preserving lineage
- R9A — independent analysis export backend: JSON / JSONL / CSV / Markdown / SRT / manifest
- R9B1 — V6 analysis-only Workspace/export integration
- R10A — Synthetic/Human-Gold benchmark and KPI semantics
- R10B0 — exact-frame native-media frame source / label-blind pilot / Human Gold compiler/preflight
- R10B1 — calibrated-profile ROI/slice extraction, manifest, checksum reference-index training and recorded-video orchestration
- R10B2 — lower-left four-slot Survivor state recognition, upper-right OCR, bottom-right four-slot Perk Top-K/UNKNOWN, Killer/Power patch-aware knowledge + visual reference recognition
- R10B3 — bounded Cross-modal Fusion for Vision/HUD/OCR/ASR/Audio/Knowledge/State
- R10B4 — explicit-authority OpenAI/Anthropic/Google Commentary LLM integration through existing BVP provider routing + deterministic Fact Validation
- R10B5 — revisioned Commentary Trivia Knowledge, manual entry, commentary/ASR Transcript candidate mining, Human Verify, contextual reuse, usage history, and `BAI DbD Trivia Editor.exe` build definition
- R10B5A — `BAI DbD Training Studio.exe` source/build contract: single sample, CSV one/many, direct video exact-frame ROI slice learning, upper-right video OCR candidate review, direct/local-ASR video Trivia mining, transcript mining, and reference/vocabulary build
- TASK-036 P-UX-2 current implementation revalidated through D3; A0-D3 focused suite `102 PASS`

## Recognition accuracy boundary

The recorded-video recognition code is now implemented, but the bundled/default ROI coordinates and deterministic dHash reference matching are **discovery/baseline contracts**, not Production accuracy evidence.

Still required:

- real DbD recordings under permitted rights;
- calibrated ROI profiles for actual resolution/UI scale;
- reviewed Perk/Killer/Power/Survivor slice references;
- upper-right Japanese/English OCR evaluation with the actual capture profile;
- match-separated held-out Human Gold Dataset;
- KPI-driven threshold/hard-negative iteration;
- learned embedding/CNN model only if the deterministic baseline is insufficient.

## Windows gates

### Main BVP EXE / R9B2

Harness is implemented but not executed on the current Linux host:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-task049-r9b2-packaged-smoke.ps1 -EvidenceDirectory .\evidence\task049-r9b2
```

### Trivia Editor EXE

Build definition is implemented but not executed on the current Linux host:

```powershell
.\build-dbd-trivia-editor-exe.bat
```

Expected output:

```text
builds\BAI DbD Trivia Editor\BAI DbD Trivia Editor.exe
```

### DbD Training Studio EXE

Build definition is implemented but not executed on the current Linux host:

```powershell
.\build-dbd-training-studio-exe.bat
```

Expected output:

```text
builds\BAI DbD Training Studio\BAI DbD Training Studio.exe
```

The Training Studio is the normal GUI route for one-item, CSV one/many and direct-video teacher-data intake. Video-derived OCR strings require Human selection; video-derived Trivia remains CANDIDATE.

## R8B remains parked

No generic Game Intelligence -> Production mutation adapter is authorized. Existing BVP authorities remain domain-specific: Asset/Slot, Narration Asset generation, Subtitle Workspace, Cut/Highlight review, Production Timeline and Resolve.

## Verification

Latest final local verification after recognition/knowledge hardening:

- all repository `tests/test_*.py`: **2128 PASS / 1 Windows-only SKIP / 0 FAIL / 0 DESELECT**;
- TASK-049 focused suite after HUD Calibration/Data Migration: **164 PASS**; calibration/migration/docs smoke: **26 PASS**;
- `python -m compileall -q src`: PASS;
- `git diff --check`: required before final commit/package.

The single skip is the existing TASK-047 Inno Setup acceptance gate and is unrelated to TASK-049.

## README / user documentation entry points

README links directly to:

- main Windows EXE build / use;
- DbD recognition accuracy / training;
- slice Dataset extraction / reference-index training;
- Trivia Knowledge lifecycle;
- Trivia Editor EXE build / use;
- DbD Training Studio EXE build / use, including direct video learning.

## Restart context

Read only:

1. root `AGENTS.md`
2. `docs/ai-team/current-state.md`
3. `docs/ai-team/tasks/TASK-049/task.md`
4. `docs/ai-team/tasks/TASK-049/TASK-049-ATOMIC-IMPLEMENTATION-PLAN.md`
5. this handoff
6. direct source/tests for the selected next gate

Do not reload the complete DbD Ver.2.2 evidence document unless a specific section is required.

## Best next action

1. execute the main BVP, Trivia Editor and DbD Training Studio Windows packaging gates;
2. admit real DbD media;
3. calibrate `DBDHudRoiProfile` and build reviewed slice indexes;
4. run recorded-video recognition + Human Gold KPI;
5. use measured confusion/hard-negative evidence to improve reference data or introduce a learned model only where necessary.

## Windows EXE / environment documentation refresh

The repository now has a dedicated build guide for every user-facing Windows EXE / installer builder currently tracked by the project:

- main BAI Video Production desktop EXE;
- DbD Training Studio EXE;
- DbD Trivia Editor EXE;
- Voice Model Builder installer / EXE;
- OBS Voice Capture installer.

`README.md` links to `docs/windows/WINDOWS-EXE-BUILD-INDEX.md`, which is the canonical build-entry page. `docs/windows/WINDOWS-GAME-INTELLIGENCE-ENVIRONMENT.md` documents Task-049 Windows prerequisites including FFmpeg, Tesseract OCR, Faster-Whisper, and current cloud-LLM configuration. Current Task-049 cloud commentary does not require a provider Python SDK and does not yet implement a local Ollama/LM Studio adapter.


## Kamigame Knowledge Candidate Import extension

The branch now includes a bounded `COMMUNITY_REFERENCE / CANDIDATE` collector for the Owner-supplied Kamigame Survivor Perk, Killer Perk and Killer-list pages, including optional Killer detail traversal and bounded pagination discovery. Training Studio exposes a **Knowledge Import** tab and README links to `docs/game-intelligence/DBD-KAMIGAME-KNOWLEDGE-IMPORT.md`. The collector preserves raw HTML + SHA-256 but never auto-writes VERIFIED canonical Knowledge. Latest broad regression: `2140 PASS / 1 Windows-only SKIP / 0 FAIL`. Live network collection remains operator-host evidence.
