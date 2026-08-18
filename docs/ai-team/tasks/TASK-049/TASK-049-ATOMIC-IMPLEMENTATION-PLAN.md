# TASK-049 — Atomic Implementation Plan

- Status: `IMPLEMENTATION-READY PLAN`
- Rule: each unit completes `Design check -> Implement -> Focused tests -> required regression -> Evidence/diff -> Commit-ready`
- Context rule: load only Current State, this Task/unit, direct dependencies, target schemas/source/tests; expand only on contradiction.
- Cost rule: use the README `AUTONOMY` adaptive model/governance example rather than one model/depth for every operation.

## R1 — Canonical Game Event Contract Foundation

**Depth:** HIGH ASSURANCE / DEV-3

**Primary capability:** High-Reasoning for boundary/schema/Critic, Implementation for code, Bulk for fixtures/docs.

**Load first:**

```text
docs/ai-team/current-state.md
docs/ai-team/tasks/TASK-009/task.md
TASK-049 integration design
docs/ai-team/tasks/TASK-022/detailed-design.md
schemas/asset-record.schema.json
schemas/evidence-record.schema.json
src/ai_video_production/dbd_profile.py
src/ai_video_production/serialization.py
src/ai_video_production/schema_contracts.py
tests/test_task009_dbd_profile.py
```

**Deliver:**

- match/evidence/event/review/knowledge-ref schemas;
- packaged schema resources;
- immutable Python contracts;
- exact rational source range type;
- closed enums and fail-closed validation;
- deterministic serialization/hash where consistent with BVP conventions.

**Do not implement:** detector, SQLite store, UI, production bridge.

**Acceptance:** schema roundtrip, package parity, float rejection, invalid range rejection, confirmed-without-evidence rejection, R0 regression green.

## R2 — Game Intelligence Store / Revision / Resume

**Depth:** STANDARD-HIGH / DEV-2 to DEV-3 for migration decisions

**Load:** R1 output + existing BVP persistence/atomic-write patterns only.

**Deliver:**

- project-local store;
- append-only event revisions/reviews;
- deterministic readback;
- transaction boundaries;
- checkpoint/resume manifest;
- corruption/unknown-version fail closed;
- export-neutral query service.

**Acceptance:** interrupted write test, revision preservation, deterministic readback, unknown schema/store version rejected.

## R3 — BVP Asset / Media / ASR / Timebase Adapters

**Depth:** STANDARD / DEV-2

**Load:** R1/R2 + TASK-003/TASK-004/TASK-006/TASK-022 contracts and exact source/tests.

**Deliver:**

- Asset adapter;
- normalization/timebase adapter;
- transcript/ASR evidence adapter;
- no duplicate Asset/ASR implementation;
- source frame alignment into Game Evidence.

**Acceptance:** exact mapping fixtures including NTSC; ASR evidence references existing transcript artifacts; no float canonical timestamps.

## R4 — Bounded DbD Feature Producers / Event Resolver

**Depth:** STANDARD-HIGH / DEV-2, Critic high-reasoning

**Deliver first vertical slice:**

```text
MATCH_START
CHASE_START
CHASE_END
INJURY
HOOK
UNHOOK
WINDOW_VAULT
PALLET_DROP
UNKNOWN_EVENT
```

Synthetic/bounded producers may be used before real-media accuracy work. The goal is contract correctness and UNKNOWN behavior, not broad recognition claims.

**Acceptance:** Evidence -> Candidate -> Event path; low confidence remains NEEDS_REVIEW/UNKNOWN; no LLM-only confirmation.

## R5 — DbD Game Knowledge / Perk Baseline

**Depth:** HIGH for schema/responsibility, then STANDARD implementation

**Load:** R1/R4 + input-evidence Perk chapters + only relevant knowledge/RAG patterns.

**Deliver:**

- perk identity/revision/environment/source provenance;
- LIVE/PTB separation;
- alias resolver;
- patch-compatible exact lookup;
- event `knowledge_ref` binding;
- initial icon/observation contract, even if full recognizer accuracy is not yet implemented.

**Acceptance:** incompatible revisions fail closed; VERIFIED facts always have provenance; event records do not duplicate mutable effect text.

## R6 — Human Review

**Depth:** STANDARD / DEV-2

R6 is intentionally split to avoid colliding with the separately owned TASK-036 V6.1.1 shell lane.

### R6A — Review backend / read model

**Deliver:**

- review queue projection with exact Event/Evidence/history;
- append-only Human Confirm/Approve/Correct/Reject/UNKNOWN application service;
- atomic Event revision + Review persistence through the existing R2 Store;
- no shared shell/UI mutation.

**Acceptance:** Human decisions preserve the old Event revision, create an auditable new revision/review, and never write Production Timeline state.

### R6B — Human Review Workspace UI

**State:** `LOCAL IMPLEMENTED / OWNER OWNERSHIP REVALIDATION SATISFIED / WINDOWS PACKAGE READ-BACK PENDING`

**Ownership gate:** satisfied by Owner instruction on 2026-08-18 after TASK-036 P-UX-2 current-source revalidation. The implementation must remain an explicitly marked additive TASK-049 extension.

**Deliver after gate:**

- Match view;
- Event Timeline;
- Event detail/evidence;
- Approve/Confirm/Correct/Reject/UNKNOWN controls;
- Perk review minimum surface.

**Acceptance:** UI is a projection/application client of R6A; it does not invent a second review truth or directly mutate Production Timeline state.

## R7 — RAG / Commentary / Fact Validator

**Depth:** STANDARD-HIGH for factual boundary, STANDARD implementation

**Deliver:**

- patch-aware knowledge retrieval;
- commentary planner;
- abstention policy;
- fact validator;
- commentary candidate store/export.

**Acceptance:** missing/incompatible knowledge does not become asserted fact; fabricated numbers/status/activation claims rejected.

## R8 — GameEventToProductionBridge

**Depth:** STANDARD-HIGH because cross-canonical boundary

R8 is split so the cross-canonical contract can close without prematurely taking ownership of existing BVP Production authority.

### R8A — proposal compiler

**Deliver:**

- side-effect-free highlight/narration/subtitle proposal bundle compiler;
- exact source-frame/rational-rate preservation;
- Event / Commentary / Evidence / Knowledge hash lineage;
- explicit `PROPOSAL_ONLY` / Human-adoption-required authority state.

**Acceptance:** only a CONFIRMED, admitted Event plus a VALIDATED non-abstaining Commentary candidate is bridgeable; no Production Timeline / Resolve / external write occurs.

### R8B — existing BVP adoption adapter

**Deliver:**

- explicit adoption service into existing BVP production-domain contracts;
- provenance from adopted production object back to the R8A proposal bundle;
- no second edit-plan or approval authority.

**Gate:** before implementation, revalidate ownership of the exact Production application-service paths. Shared TASK-036 UI/Shell ownership is not implied by this unit.

**Acceptance:** rejected/unadopted proposal produces no production mutation; adoption must pass existing BVP authority/application contracts.

## R9 — Independent Analysis Workflow + Windows Test EXE

**Depth:** STANDARD; packaging critical checks follow existing Windows contract

R9 is split so analysis-only export can close before shared V6 UI / packaged-shell ownership is taken.

### R9A — analysis-only export backend

**Deliver:**

- deterministic latest-event analysis export;
- `analysis.json`, `events.jsonl`, `events.csv`, `report.md`, `commentary.srt`;
- artifact-hash manifest;
- exact rational source-clock SRT timing;
- no Production Timeline / Resolve / external publish side effect.

**Acceptance:** local analysis can be completed/exported without entering Production; uncertain Events remain visible in analysis artifacts but cannot become SRT commentary without validated current-revision commentary.

### R9B — BVP Workspace + packaged Windows test build

**State:** `R9B1 V6 WORKSPACE LOCAL PASS / R9B2 WINDOWS PACKAGED TEST BUILD PENDING`

**Deliver:**

- BVP Home/Workspace entry for Game Intelligence;
- analysis-only end-to-end UI path;
- packaged Windows test build through existing BVP build contract;
- restart/readback smoke test.

**Gate:** shared TASK-036 V6.1.1 UI/Shell ownership was revalidated by Owner on 2026-08-18. R9B2 still requires an actual Windows packaging/read-back environment.

**Acceptance:** user can finish an analysis project without entering production editing; no second EXE is created.

## R10 — Native DbD Pilot / Gold Dataset / Accuracy Gate

**Depth:** HIGH ASSURANCE for acceptance claims

R10 is split so metric semantics can be fixed before any real-media quality claim.

### R10A — benchmark / KPI contract

**Deliver:**

- versioned Synthetic / Human-Gold benchmark case contracts;
- exact Event label / range / expected-abstention semantics;
- Precision / Recall / F1 / False Positive / False Negative metrics;
- Unknown Detection / Abstention Correctness;
- calibration error;
- timing error in thousandths of a source frame;
- deterministic dataset/report hashes.

**Acceptance:** the evaluator measures supplied predictions only and always records that no native-media evidence or production accuracy authorization has been established.

### R10B — recorded-video recognition / Human Gold pilot

**State:** `R10B0-R10B5 BOUNDED BASELINES IMPLEMENTED / REAL-MEDIA CALIBRATION + HUMAN GOLD KPI PENDING`

#### R10B0 — native pilot infrastructure

Implemented:

- label-blind Human-Gold evaluation-window contract;
- exact bounded FFmpeg frame source;
- detector Protocol;
- detector -> Evidence -> R4 Resolver -> CGEL -> KPI runner;
- dataset/report integrity and explicit no-production-accuracy-authority semantics.

#### R10B1 — ROI / slice dataset and recorded-video recognizer

Implemented baseline:

- calibrated/discovery `DBDHudRoiProfile` contract with four Survivor and four Perk slots;
- exact-frame ROI slice extraction + provenance manifest;
- checksum-protected reference-index training with visual-state `group` metadata;
- recorded-video orchestration across lower-left HUD, upper-right OCR, bottom-right Perks and optional Killer/Power ROI.

Remaining gate:

- calibrate ROI profiles on real recordings and build match-separated labeled reference data.

#### R10B2 — HUD / Perk / Killer-Power recognition

Implemented baseline:

- Survivor states `HEALTHY / INJURED / DOWNED / HOOKED / DEAD / ESCAPED / UNKNOWN`;
- exact transition candidates for INJURY / DOWN / HOOK / UNHOOK / KILL / ESCAPE;
- four-slot Perk Top-K / UNKNOWN / temporal vote;
- optional Tesseract upper-right OCR + bounded DbD vocabulary;
- patch-aware/source-provenanced Killer/Power store + reference recognition.

Remaining gate:

- populate reviewed Perk/Killer/Power data and real slice references; measure held-out accuracy.

#### R10B3 — Cross-modal Fusion

Implemented baseline:

- VISION / HUD / OCR / ASR / AUDIO / KNOWLEDGE / STATE observation contract;
- ambiguity fail-closed behavior;
- independent-modality confidence bonus;
- weak single-modality review/abstention behavior.

Remaining gate:

- tune weights/thresholds only from real Human Gold evidence.

#### R10B4 — LLM Commentary provider integration

Implemented:

- existing BVP OpenAI / Anthropic / Google planning provider routes;
- explicit execution authorization and user cost confirmation;
- strict JSON claim contract;
- deterministic Fact Validator after provider output;
- no CGEL/Production mutation authority for provider output.

Remaining gate:

- external provider runtime evidence is not created automatically and remains an explicit authorized execution.

#### R10B5 — Commentary Trivia Knowledge / manual maintenance utility

Implemented:

- revisioned CANDIDATE / VERIFIED / REJECTED / SUPERSEDED Trivia Store;
- manual registration;
- commentary and ASR Transcript candidate mining with provenance;
- patch/event/entity-aware VERIFIED retrieval;
- Commentary Planner reuse + usage history;
- separate `BAI DbD Trivia Editor.exe` build definition and operation guide.

Remaining gate:

- actual Windows Trivia Editor build/run evidence on a Windows host.

#### R10B6 — real-media calibration / accuracy gate

Deliver with real DbD recordings:

- match-separated Human Gold Dataset;
- calibrated ROI profiles;
- reviewed Perk/Killer/Power reference datasets;
- measured Precision / Recall / F1 / False Positive / False Negative / UNKNOWN / calibration / timing metrics;
- confusion-pair and hard-negative loop;
- learned CNN/embedding replacement only if the deterministic baseline KPI proves insufficient.

**Gate:** R10B6 requires real DbD media + Human labels. Any production-quality threshold remains explicit Owner/Judge policy, not an inferred metric.

**Acceptance:** measured values only; production-quality claims forbidden until threshold policy is explicitly approved.

## Global Human Gates

The following remain Human/Owner gated regardless of unit:

- paid Provider execution;
- credential entry/change;
- real Resolve/Cubase or other external mutable app write when target is not already explicitly authorized;
- destructive migration;
- release/tag/deploy/publication;
- production activation;
- rights/consent override;
- final UX acceptance when required by current BVP governance.

## Context economy example for this program

Start with:

```text
current-state
TASK-009
current R-unit
only direct dependencies
necessary schemas
relevant src
relevant tests
```

For example R3 adds TASK-003/004/006/022; R5 adds Perk Knowledge input evidence. Do not make every R-unit re-read the complete 140KB DbD source design or the entire BVP documentation tree.
