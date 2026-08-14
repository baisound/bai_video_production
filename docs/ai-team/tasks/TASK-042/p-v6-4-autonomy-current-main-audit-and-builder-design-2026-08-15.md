# TASK-042 — P-V6-4 AUTONOMY Current-main Audit and Builder Design

## 1. Authority and Source of Truth

- Product Authority: `BAI VIDEO PRODUCTION`
- Owner priority: `OWNER_MAXIMUM / CURRENT_HIGHEST`
- Fresh checkout: clean main `c6a5cb108032709615ab99856890d0a3709d7d5d`
- Branch: `codex/task-042-p-v6-4-design`
- P-V6-3 Closure Sync: PR #60 merged at exact main
  `c6a5cb108032709615ab99856890d0a3709d7d5d`; branch/clone cleanup passed
- Handoff status: current checkout is newer and is the implementation Source of
  Truth
- Handoff manifest checksum:
  `sha256:d35a32cca95382a6e8e4ff0f66d6df69100beae579aa9ee0b85f0af68dee260c`
- Bootstrap checksum:
  `sha256:b1c1709c4b00fbac5887de9fe1f3ae5deab816d13277575ac1816ba6b4342cdc`
- Autonomous Queue result: `RUNNABLE_TASK_SELECTED`
- Selected: `BVP-TASK-042-P-V6-4-DESIGN / DESIGN_ONLY`
- Queue checksum:
  `sha256:23e42b59c3a95ceb41e2f92af06f128d7ded8ff5b847458d4438419cbc114015`
- Waiting: P-V6-4 Implementation and P-V6-5 Design
- Parked: TASK-013 Native H3, TASK-014 paid narration execution and
  unauthorized OS TASK-017
- System blocked: `false`

This design is the second merge in the current two-merge cadence only after its
exact hosted head is green, merged and cleaned up. It does not authorize source
implementation on this branch.

## 2. Current OS audit

The BAI Development OS autonomy contracts were executed on the fresh clone:

1. Handoff Bootstrap selected current clean main instead of stale handoff text.
2. Autonomous Queue selected only P-V6-4 Design and kept implementation in
   dependency wait.
3. Native H3 and paid TASK-014 execution remained task-locally parked.
4. OS TASK-017 was not confused with Product TASK-042.
5. Context loading remained task-bounded; provider/cached/output/billed token
   fields are unavailable and are not invented.

No BAI Development OS runtime dependency is added to the Product.

## 3. Registry and implementation audit

| Required truth/capability | Current owner | Exact current state | P-V6-4 decision |
|---|---|---|---|
| Project/Scene timing | TASK-027/TASK-042 Blueprint v2 | exact rational rate, contiguous Scene frame ledger and target duration | remains the only timing authority |
| Scene audio intent | Blueprint v1/v2 | booleans plus SE text labels; no Timeline ranges | proposal input only; never placement truth |
| Audio Candidate/LOCK/STALE | TASK-037 | canonical Slot/Candidate lifecycle for SE/BGM/NARRATION | reuse; add first-class `AMBIENCE` Slot kind compatibly |
| Human Audio review | TASK-041 | durable Candidate-bound PlacementReview and one-shot ACCEPT/REJECT/ALTERNATE_USE | remains the only placement review/decision truth |
| Placement compilation | TASK-026 | exact frames, snap, loop, fade/gain and TASK-010 compatibility failure | reuse after current Timeline-bound review is accepted |
| Narration planning | TASK-014 | private script hash, voice profile, paid-execution gate and alignment-to-ms cues | reuse planning/alignment; paid Provider remains parked |
| Subtitle/SRT editing | TASK-006 | revisioned ms cues and SRT import/export | project SRT is a proposal surface, not Scene timing authority |
| Provider/local generation | TASK-013/TASK-014 | separately authorized and Human/cost gated | no dispatch in this slice |
| Resolve/Cubase mutation | TASK-010/TASK-012 | separate native/external authority | not started by P-V6-4 |

### 3.1 Current gaps confirmed on exact main

1. `CRITICAL`: the required source-of-truth decision is unresolved. Letting SRT
   and Scene timing update each other would allow silent Timeline mutation.
2. `HIGH`: Scene audio booleans cannot express whole-video or arbitrary-range
   BGM, cue-based SE, range-based ambience, narration gaps or parallel lanes.
3. `HIGH`: TASK-041 placement rows do not bind the Blueprint/Timeline plan and
   item revision. A once-valid review can otherwise be compiled after timing
   changes.
4. `HIGH`: there is no durable, restart-safe Timeline audio plan history or CAS
   application boundary.
5. `HIGH`: ambience has no first-class TASK-037/TASK-041/TASK-026 role and must
   not be silently mislabeled as SE or OTHER.
6. `HIGH`: TASK-026 intentionally fails on unsupported execution semantics, but
   no Product projection explains blockers for stretch/crossfade or changed
   Timeline bindings.
7. `MEDIUM`: TASK-014 alignment produces millisecond cues while Blueprint v2 is
   frame-authoritative; an exact deterministic conversion/conflict rule is
   missing.

Baseline is the P-V6-3 Closure Sync main with full `987 / 987 PASS` and one
intentional platform skip. Stable Product release remains `v0.20.1`.

## 4. DEV Profile re-decision

- Blast radius: Blueprint timing, Audio Candidate/Review/Placement truth,
  narration/SRT projection and future Resolve compilation.
- Authority risk: an edited SRT or old review could mutate or compile against
  the wrong Timeline.
- Recovery risk: cross-snapshot CAS, restart, plan rebase and historic accepted
  placements.
- Compatibility risk: existing Production Control and Audio Workspace snapshots.
- External/cost risk: paid narration, generation, media and native NLE/DAW.
- Decision: `DEV-4 FOUNDATION CRITICAL`.

Required process is exact Allowed Files, two Critic cycles, compatibility/
security/recovery tests, full regression, hosted matrix, exact main verification
and cleanup.

## 5. Builder design

### 5.1 Timing Source of Truth and SRT adjudication

`ProductionBlueprintV2.timeline_rate`, contiguous Scene frame ranges and
`target_duration_frames` are authoritative. P-V6-4 never changes them.

Master SRT is a derived/editable proposal over canonical frame-based narration
cues. An SRT edit may propose new cue text or timing, but it cannot move Scene
boundaries or silently rewrite a Timeline plan. Import/reimport creates a new
proposal with explicit conflicts. The Human resolves conflicts by creating a new
Timeline audio plan revision or by separately revising the Blueprint.

Canonical cues store frames, text reference/hash and origin, not SRT millisecond
round trips. Export formats start/end deterministically from rational frames.
Import converts milliseconds by one documented rational rule and records any
rounding delta. A cue outside the target duration, with end before/equal start,
overlapping narration on the same lane, crossing its bound Scene unexpectedly,
or mismatching expected text/Blueprint identity is `CONFLICT` and cannot be
placed.

A Blueprint checksum/rate/range change makes the current Timeline audio plan
`STALE_REBASE_REQUIRED`. Rebase produces a new revision and never overwrites the
old plan or accepted placement evidence.

### 5.2 Timeline audio domain

Add `timeline_audio.py` with closed immutable contracts:

- `TimelineAudioPlan`: project/plan/revision, exact Blueprint ID/hash, rational
  rate, target duration, previous plan hash and sorted items;
- `MusicPlan`: `WHOLE_TIMELINE` or explicit range, source intent and lane;
- `NarrationCue`: exact frame range, Scene binding, text reference/hash and
  proposal/conflict state;
- `AudioCue`: cue-oriented SE with exact start/duration;
- `AudioRange`: BGM or AMBIENCE with exact start/end;
- `TimelinePlacementBinding`: exact plan/revision/hash, item ID/hash and
  Blueprint hash;
- `SrtProposal`: exact source hash, cue mappings, rounding observations and
  conflicts.

All ranges are end-exclusive integer Timeline frames. IDs, ordering and hashes
are deterministic. Items bind an exact TASK-037 Slot and may bind an exact
Candidate/Asset/checksum only when one exists. They do not create Candidate,
Audit, LOCK or media state.

BGM supports a whole-video range or multiple named ranges independent of Scene
boundaries. SE is cue-oriented. Ambience is range-oriented. Narration may be
absent for any Scene. Parallel lanes are explicit. Same-lane overlaps fail
closed except for a bounded BGM transition that declares both exact items and a
crossfade range. Stretch/crossfade intent may be recorded, but unsupported
TASK-026/TASK-010 execution remains a visible blocker.

### 5.3 First-class ambience without lifecycle duplication

Add `AMBIENCE` compatibly to the existing TASK-037 `SlotKind`, TASK-041
`AudioSlotKind`/track role and TASK-026 `AudioPlacementRole`. Existing enum
values and serialized records remain unchanged. The Production Control schema is
updated additively. Ambience uses the existing Candidate -> Audit -> ACCEPT ->
LOCK lifecycle and existing Audio Workspace review; no parallel registry is
created.

### 5.4 Durable Timeline plan history

Add `timeline_audio_store.py`. It persists only immutable Timeline plan revisions
and the current revision pointer in bounded `timeline-audio.json`:

- strict known fields and version;
- canonical checksum and maximum size;
- no Prompt/script bodies, media bytes, host paths or credentials;
- atomic replace, symlink/path containment checks and exact previous-checksum
  CAS;
- append-only `(plan_id, revision)` and previous-hash chain;
- legacy Product projects with no file load as an empty state;
- corrupt, truncated, foreign-project, forked-history and unknown-version data
  fail closed.

This is a plan history, not a Candidate, Audio Asset, review, placement decision,
Prompt, job or Provider registry.

### 5.5 Timeline Audio application and projection

Add `timeline_audio_application.py`. The application reads exact Blueprint,
Production Control and TASK-041 Audio Workspace snapshots and owns only Timeline
plan writes.

`prepare_plan_revision -> apply_plan_revision` binds expected Blueprint,
Production and Timeline checksums to a one-shot confirmation. Apply revalidates
all inputs and writes only the Timeline store. Drift consumes and rejects the
confirmation; restart requires re-prepare.

Its projection reports each item as one of:

- `INTENT_ONLY`;
- `CANDIDATE_REQUIRED`;
- `AUDIT_OR_LOCK_REQUIRED`;
- `PLACEMENT_REVIEW_REQUIRED`;
- `PLACEMENT_HUMAN_DECISION_REQUIRED`;
- `TASK026_READY`;
- `STALE_REBASE_REQUIRED`;
- `EXECUTION_FEATURE_GAP`.

It never reports Provider/native execution as started.

### 5.6 Reuse TASK-041 as the only placement review

Extend `PlacementReview` with an optional typed Timeline binding. Legacy rows
omit the field and preserve exact serialized shape. P-V6-4 registers a review
through the existing durable TASK-041 prepare/apply transaction only after the
item binds the exact project/role Slot and a `LOCKED/CURRENT` Candidate Asset.

For a Timeline-bound row:

- TASK-041 Human decision preparation requires the exact current Timeline plan
  and item hash;
- plan/Blueprint/Candidate drift makes the one-shot confirmation stale;
- direct legacy APIs without current Timeline proof fail closed;
- Reject/Alternate Use remain history and never delete the Candidate or plan;
- a new plan revision never mutates the old review.

### 5.7 TASK-026 and execution boundary

`AudioWorkspacePlacementBinding.compile_accepted_placement` validates the exact
current Timeline binding before invoking the existing TASK-026 compiler.
Accepted legacy reviews keep their current path. A Timeline-bound review without
current proof, with changed plan/item/Blueprint/Candidate hash, unresolved SRT
conflict or unsupported stretch/crossfade fails closed.

P-V6-4 implementation may produce a deterministic TASK-026 plan in memory for a
ready item, but does not persist an execution job and does not call TASK-010,
Resolve or Cubase. TASK-026 fade/gain incompatibility with TASK-010 remains
visible and is never dropped.

### 5.8 Narration and Provider boundaries

Scene narration intent may produce a frame-based Master cue proposal. Existing
TASK-014 script/profile/plan hashes and alignment are reused. Raw narration text
is caller-owned/private and durable Timeline records contain only references and
hashes. P-V6-4 does not call ElevenLabs, resolve credentials, reserve budget,
write generated audio, create a Candidate or claim TASK-014 completion.

Existing imported/locked narration Assets can be planned and reviewed without a
paid call. BGM/SE/ambience generation similarly remains TASK-013/Quick intent and
separate execution authority.

## 6. Implementation order

1. Add exact frame-domain models, SRT proposal/conflict tests and Timeline
   authority rules.
2. Add first-class AMBIENCE roles and legacy compatibility tests.
3. Add crash-safe Timeline plan history/store and restart/corruption/CAS tests.
4. Add Timeline application revision prepare/apply and read-only projection.
5. Add optional Timeline binding to the existing TASK-041 placement record,
   persistence and Human-decision path.
6. Bind current accepted review to TASK-026 and expose unsupported feature gaps.
7. Add TASK-014 alignment/Scene-cue proposal integration without Provider calls.
8. Run focused compatibility/security/recovery tests, full regression,
   Windows/WSL2 compileall, schema and diff checks, then implementation Critic.
9. Synchronize exact local truth; publish only through a dedicated PR.

## 7. Proposed implementation Allowed Files

- `src/ai_video_production/timeline_audio.py` (new)
- `src/ai_video_production/timeline_audio_store.py` (new)
- `src/ai_video_production/timeline_audio_application.py` (new)
- `src/ai_video_production/audio_workspace.py`
- `src/ai_video_production/audio_workspace_store.py`
- `src/ai_video_production/audio_workspace_application.py`
- `src/ai_video_production/audio_workspace_placement_binding.py`
- `src/ai_video_production/audio_placement.py`
- `src/ai_video_production/production_control.py`
- `src/ai_video_production/production_control_store.py` only if compatibility
  parsing requires an explicit additive change
- `src/ai_video_production/owner_narration.py` only for the exact frame proposal
  bridge; paid execution code remains unchanged
- `src/ai_video_production/schema_resources/timeline-audio-plan.schema.json`
  (new)
- `schemas/timeline-audio-plan.schema.json` (new)
- `docs/ai-team/tasks/TASK-037/schemas/production-control-asset-registry.schema.json`
- `tests/test_task042_timeline_audio.py` (new)
- `tests/test_task042_timeline_audio_store.py` (new)
- `tests/test_task042_timeline_audio_application.py` (new)
- `tests/test_task042_timeline_audio_srt.py` (new)
- existing TASK-014/026/037/041 tests only for exact backward compatibility and
  integration coverage
- `docs/ai-team/tasks/TASK-042/**`
- bounded state synchronization: `PROJECT.md`, `CHANGELOG.md`,
  `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md`,
  `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`

No Desktop Shell/UI, Provider adapter, Credential vault, generated-media writer,
Resolve/Cubase/native runtime, package/version, Tag, Release or Deploy file is
allowed. A newly proven required file outside this list stops implementation and
returns to Builder/Critic.

## 8. Required gates

- Blueprint v2 remains the sole timing authority; SRT never mutates it;
- exact rational frame/SRT mapping, explicit rounding and conflict tests;
- whole/range BGM, cue SE, range ambience and narration-gap validation;
- AMBIENCE uses the canonical Candidate/Audit/Lock path;
- legacy Production/Audio snapshots load and serialize compatibly;
- Timeline history checksum/CAS/restart/corruption/symlink/foreign-project gates;
- old Timeline-bound reviews cannot be accepted or compiled after drift;
- TASK-041 remains the only PlacementReview/Human decision truth;
- unsupported stretch/crossfade/fade/gain never silently disappear;
- raw narration/script bodies, paths, secrets and media absent from persistence;
- no Provider, paid, Candidate, media, TASK-010, Resolve or Cubase side effect;
- focused tests, full regression, Windows/WSL2 compileall, schemas and diff;
- Critic unresolved Critical/High `0 / 0` and hosted `9 / 9`.

## 9. Design boundary

This document authorizes design review only. P-V6-4 implementation stays
`NOT_STARTED` until the exact design commit passes hosted checks, merges, cleans
up and a fresh-main BAI Development OS Queue selects the implementation unit.
