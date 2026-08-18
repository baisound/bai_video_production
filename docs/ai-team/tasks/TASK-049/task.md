# TASK-049 — DbD Game Intelligence / Canonical Game Event Timeline Integration

- Status: `R1-R10A BACKEND IMPLEMENTED / R6B+R9B1 V6 UI LOCAL PASS / R9B2 WINDOWS HARNESS READY / R10B0-R10B5B RECOGNITION+LLM+TRIVIA+HUD-CALIBRATION+MIGRATION BASELINES IMPLEMENTED / REAL-MEDIA ACCURACY + WINDOWS NATIVE GATES PENDING`
- Governance: `R1 DEV-3 HIGH ASSURANCE`; later units adaptive `DEV-2/DEV-3`
- Owner: `開発担当`
- Product: `BAI VIDEO PRODUCTION`
- Primary dependency: `TASK-009 DBDProfilePlugin R0`
- Other direct dependencies: `TASK-003`, `TASK-004`, `TASK-006/TASK-023`, `TASK-008`, `TASK-022`
- Runtime form: `ONE BAI Video Production product entrypoint`
- Standalone Game Intelligence product EXE: `NOT PLANNED`; bounded maintenance/training utilities are allowed: `BAI DbD Trivia Editor.exe` and `BAI DbD Training Studio.exe`; both have build definitions and Windows packaged execution remains NOT_EXECUTED
- Analysis-only workflow inside BVP: `REQUIRED`
- Public release / tag / deploy: `NOT AUTHORIZED`
- Shared V6 UI/Shell: `OWNER REVALIDATED / TASK-049 ADDITIVE EXTENSION AUTHORIZED 2026-08-18`


## Current implementation state — 2026-08-18

Implemented and locally verified:

- R1 CGEL contracts;
- R2 append-only Store / revision / resume;
- R3 BVP Asset/Media/ASR/exact-timebase adapters;
- R4 bounded DbD Event resolver;
- R5 patch-aware/source-provenanced Perk Knowledge baseline;
- R6A Human Review backend;
- R6B additive V6 Human Review Workspace;
- R7 Commentary / typed Fact Validator;
- R8A proposal-only Production bridge;
- R9A independent analysis export backend;
- R9B1 additive V6 analysis-only Workspace/export integration;
- R10A Synthetic/Human-Gold benchmark/KPI contract.
- R10B1 ROI/slice extraction, reference-index training, lower-left HUD, upper-right OCR and bottom-right Perk baselines;
- R10B2 Killer/Power patch-aware knowledge and visual reference recognition;
- R10B3 Cross-modal Evidence Fusion;
- R10B4 explicit-authority LLM Commentary provider integration through existing BVP provider routes;
- R10B5 revisioned Commentary Trivia Knowledge, candidate mining, verified-trivia reuse and manual Trivia Editor utility;
- R10B5A DbD Training Studio: GUI/EXE teacher-data intake for single still samples, CSV one/many, exact-frame video ROI extraction, upper-right OCR video candidates, direct/local-ASR video Trivia mining, and reference/vocabulary build.
- R10B5B HUD Calibration / Data Migration: GUI video/still ROI drag registration, normalized/versioned HUD Profile, anchor clips, fail-closed auto Profile resolve, bounded anchor correction propagated to child slots, recorded-video recognizer integration, and checksum Backup/Preview/Restore for DbD data migration.

TASK-036 P-UX-2 current-source revalidation proves A0 through D3 bounded
implementation with `102 PASS`; P-UX-2E packaged-native closure remains open.
TASK-049 shared controls are explicitly marked `data-contract-extension="TASK-049"`
and are excluded from the TASK-036 base mock-parity inventory.

Remaining:

- R9B2 Windows packaged build/restart/read-back harness is implemented; actual Windows execution remains NOT_EXECUTED on the current Linux host;
- `BAI DbD Trivia Editor.exe` and `BAI DbD Training Studio.exe` build definitions are implemented; Windows packaged execution remains NOT_EXECUTED on the current Linux host;
- R10B0 native pilot infrastructure and R10B1-R10B5 bounded recognition/knowledge/LLM/trivia baselines are implemented; real DbD media calibration, labeled reference datasets, Human Gold execution and threshold tuning remain pending;
- R8B remains parked until a domain-specific existing BVP adoption path is
  selected; no generic Production mutation adapter is authorized.

## Purpose

Integrate the DbD Video Intelligence design into BAI VIDEO PRODUCTION without duplicating existing BVP Asset, media, ASR, exact-timebase, production-timeline, Voice, Resolve, or packaging responsibilities.

The central new semantic model is the **Canonical Game Event Timeline (CGEL)**: evidence-backed game observations aligned to exact source frame/rational time. CGEL answers **what happened in the game** and remains separate from the BVP Production Timeline, which answers **how the finished video is assembled**.

## Non-negotiable boundaries

1. `TASK-009 R0` remains unchanged and data-only.
2. CGEL never becomes direct Resolve/edit mutation authority.
3. Confirmed game events require admitted Evidence; unconstrained LLM inference alone is insufficient.
4. Exact frame/rational time is canonical; floating seconds are display-only.
5. Game Knowledge facts are revisioned references, not copied mutable text inside every event.
6. `UNKNOWN` / `NEEDS_REVIEW` are valid outcomes and preferred over false certainty.
7. A standalone Game Intelligence product/installer is not part of this task. A small bounded Trivia Editor maintenance utility EXE is permitted and does not duplicate the Game Intelligence runtime.
8. Analysis may finish without entering editing; JSON/JSONL/CSV/Markdown/SRT-style outputs are later planned.
9. Paid providers, destructive migrations, external mutable app writes, release/tag/publication and production activation remain separate Human/Owner gates.

## R1 scope — Canonical contract foundation

R1 implements only:

- exact rational source range contract;
- game Match contract;
- game Evidence contract;
- Canonical Game Event contract;
- review contract;
- knowledge-reference contract;
- public JSON Schemas and byte-identical packaged schema mirrors;
- deterministic serialization / hashing consistent with BVP conventions;
- fail-closed validation;
- focused tests plus TASK-009 regression.

R1 MUST NOT implement detectors, SQLite persistence, UI, RAG, commentary, production bridge, or external effects.

## R1 acceptance

- public/package schema mirrors are byte-identical;
- schemas are Draft 2020-12 valid;
- rational frame rate rejects float canonical representation;
- ranges are non-negative and end-exclusive;
- reduced rational values are deterministic;
- invalid enum / identifier / confidence values fail closed;
- `CONFIRMED` event with no evidence is rejected;
- `TASK-009` R0 focused tests remain green;
- `git diff --check` is clean.

## Next units

See `TASK-049-ATOMIC-IMPLEMENTATION-PLAN.md`.
