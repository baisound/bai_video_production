# TASK-026 P-AUDIO-1 Current-main Audit and Product Promotion Builder Design

Date: `2026-08-15`
Authority: `AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE`
Starting Source of Truth: exact clean main
`5e061fb5d7463c00ad893d28fdf0cbb9b480b1ba`
Working branch: `codex/task-026-audio-placement-product-promotion-design`
Selected unit: `BVP-TASK-026-P-AUDIO-1 / AUDIO_PLACEMENT_PLAN_PRODUCT_PROMOTION`
Mode: `DESIGN_ONLY`

## 1. Problem and current-state audit

PR #84 exact head `ab50e99261f05e3cf70211ee03cc77740ba901b6`
passed hosted `9 / 9` and merged at the exact starting main above. Its remote
branch and clean dedicated checkout were removed. This fresh checkout has no
open PR, dirty change, local/remote divergence or colliding TASK-026 branch.

Stable Product package/Tag/Release remain `0.21.0 / v0.21.0 / stable` at
release-code SHA `c38187ed54e3601c44411d9b8a128348b0d8a7b7`. Current development
main is newer. No post-0.21.0 version is selected.

The Task Registry currently groups TASK-025 and TASK-026 as `NOT_STARTED /
NOT_AUTHORIZED`, but current code and accepted documents prove that statement
is too broad:

- `audio_placement.py` already implements deterministic exact-frame snap,
  loop/bed, fade/gain retention, plan hashing and explicit TASK-010
  compatibility;
- `audio_workspace_placement_binding.py` already requires a Human-accepted
  TASK-041 Placement, a LOCKED TASK-037 Candidate and, for the V6 route, an
  exact current TASK-042 Timeline Audio binding;
- focused TASK-026/TASK-041/TASK-042 tests already cover those foundations;
- TASK-041 Product Application and Shell deliberately stop before TASK-026;
- TASK-042 persists the authoritative Timeline Audio plan but retains
  `task026_compile_started=false`;
- no durable Product Application, Project child history, restart projection or
  Shell confirmation currently compiles and records a TASK-026 Plan.

Classification:

- deterministic placement domain: `ALREADY_IMPLEMENTED`;
- TASK-041/TASK-037/TASK-042 compile binding: `ALREADY_IMPLEMENTED`;
- Task Index state: `CONFLICTS_WITH_CURRENT_CANONICAL_IMPLEMENTATION`;
- durable Product integration: `NEW_CAPABILITY_REQUIRED`;
- Provider/audio generation/TASK-010 external application: `DEFER / SEPARATE
  HUMAN_OR_NATIVE_GATE`.

This is the highest safe remaining dependency-first Product integration.
TASK-013 Native H3 remains parked after the force-restart incident, TASK-014
paid narration remains a Human Gate, and full TASK-027 orchestration depends on
durable audio placement rather than another duplicate planning foundation.

## 2. DEV Profile re-decision

`DEV-4 PRODUCT ORCHESTRATION CRITICAL` is required. The bounded change crosses
Product Project persistence, Production LOCK truth, Human Audio review,
Timeline revision truth, derived placement Evidence and the unified Shell. A
stale or caller-forged Plan could later direct audio to the wrong Asset, range
or track.

Safety floor:

- derive, never accept, Candidate/Asset/Timeline/Plan identity;
- require exact Human ACCEPT plus Candidate LOCK;
- append immutable compilation Evidence; never overwrite history;
- bind exact upstream snapshot checksums and derive CURRENT/STALE;
- no Provider, paid, media-byte, TASK-010, Resolve or Cubase execution;
- use TASK-043 coordinated Product save and recovery interlock;
- strict legacy-empty and unknown-format behavior;
- two Critic rounds with unresolved Critical/High `0 / 0` before implementation.

## 3. Domain ownership and non-goals

TASK-041 remains Human placement-review authority. TASK-037 remains
Candidate/LOCK/STALE authority. TASK-042 remains Project Timeline Audio
authority. TASK-026 owns only deterministic derived Audio Placement Plans.
TASK-010 remains the sole Resolve assembly/mutation owner.

P-AUDIO-1 does not:

- generate, download, transcode, normalize or copy audio bytes;
- call any local/cloud Provider or paid route;
- create or change a Candidate, Audit decision, ACCEPT or LOCK;
- call `to_task010_audio_placements()` as an execution shortcut;
- mutate Resolve, Cubase, a human-owned Project or any NLE;
- auto-compile on Human ACCEPT, Project open or restart;
- select a version, Tag, Release or Production Deploy.

## 4. Durable model and schema

Add a Product Project child at
`state/audio-placement-history.json` with format
`bai-video-production.audio-placement-history / 1.0.0`.

The document contains:

- exact `project_id` and monotonic `store_revision`;
- append-only bounded compilation records;
- a checksum over the complete body.

Each record contains:

- deterministic `compilation_id`;
- exact TASK-041 `review_id`, decision and Audio snapshot SHA-256;
- exact TASK-037 Slot/Candidate/Asset ID and Asset SHA-256 plus Production
  snapshot SHA-256;
- exact TASK-042 Timeline plan ID/revision/hash, item ID/hash and Timeline
  snapshot SHA-256;
- requested `track_index` and `bed_mode` confirmed by the Human;
- the complete deterministic TASK-026 `AudioPlacementPlan` and its hash;
- source Product Manifest revision/hash for audit provenance;
- `task010_structurally_compatible`, never `execution_ready`;
- invariant false Provider/paid/media/external mutation authority fields.

The compilation identity is derived from the exact upstream bindings, track
intent, bed mode and Plan hash. It excludes timestamps and the new output
Manifest hash, avoiding a self-referential or always-stale identity.

Maximum records and serialized bytes are bounded. IDs, checksums, enums,
integers and unknown fields are strict. Prompt bodies, transcript text,
credentials, media bytes and absolute host paths are prohibited.

## 5. Versioning, migration and backward compatibility

- A Product Project without a TASK-026 child loads as an empty compatible
  history.
- A legacy launcher Project without a Product Manifest does not receive one
  implicitly. TASK-041 review remains available and the TASK-026 Product action
  is projected unavailable until the governed Product Project/Timeline exists.
- If the child file exists without an exact Product Manifest binding, fail
  closed as an unbound-file security error.
- Unknown format/version, partial rows, duplicate identities, checksum drift,
  non-monotonic revision or impossible authority flags fail closed.
- No historical Product Project or TASK-041/TASK-042 document is rewritten.
- The generic TASK-043 child-binding format is already additive, so the Product
  Manifest schema needs no new field or breaking migration.

## 6. Application Service

Add `Task026AudioPlacementApplication` scoped to one resolved regular Project
root and exact Project ID.

### 6.1 Snapshot

Snapshot loads and verifies:

1. current Product Manifest and TASK-043 recovery status;
2. current TASK-037 Production snapshot;
3. current TASK-041 Audio Workspace snapshot;
4. current Manifest-bound TASK-042 Timeline Audio history;
5. current Manifest-bound TASK-026 compilation history.

It projects bounded runnable reviews and historical compilations. A record is
`CURRENT` only when the exact current review, Candidate/LOCK, Asset bytes
identity, Timeline binding and three upstream snapshot checksums still match.
Otherwise it is `STALE` with deterministic reason codes. History is retained.

### 6.2 Prepare

The caller supplies only:

- `review_id`;
- `track_index`;
- `bed_mode`;
- expected Product, Production, Audio, Timeline and TASK-026 snapshot hashes.

The service derives every other identity, calls the existing
`compile_current_timeline_placement()` binding and returns one one-shot
confirmation with the exact Plan, compatibility limits and all authority flags
false. It rejects pending TASK-043 recovery, stale snapshots, non-ACCEPT review,
non-LOCKED Candidate, missing/current-mismatched Timeline proof, STRETCH and
invalid source duration before any write.

### 6.3 Apply

Apply consumes the confirmation once, acquires a project-scoped update lock,
reloads every upstream, re-derives the Plan and requires byte-logical equality
with preparation. It appends at most one deterministic record. An exact
existing record is idempotent; an identity collision with different content is
a data-integrity error.

The new child plus incremented Product Manifest commit through
`ProductProjectSaveCoordinator`, child first and Manifest last, with exact
previous Manifest CAS. If the coordinated save is interrupted, TASK-043 owns
COMPLETE/ROLLBACK recovery and no compile is automatically replayed.

Upstream state may change after commit. That cannot make the historical record
false: the next snapshot derives it as STALE and no external operation can use
it. No automatic deletion or recompilation occurs.

## 7. Shell interaction and accessibility

Extend the existing Audio Workspace, not a new competing window:

- accepted/locked/current-Timeline rows show `Placement Planを作成`;
- the action requests bounded track index and PREVIEW/FULL intent;
- a native browser confirmation displays Candidate, Asset logical ID, exact
  frame range, role, loop/fade/gain, compatibility gaps and the statement that
  Resolve/Cubase/audio generation will not start;
- apply refreshes compiled history with `CURRENT`/`STALE`, Plan hash and visible
  reason codes;
- buttons use semantic labels, keyboard focus and existing error handling;
- no host path, Prompt/transcript body or credential is rendered;
- no `Execute`, `Render`, `Resolveへ適用` or blanket action is introduced.

The trusted launcher composes the TASK-026 application only when an exact
Product Manifest exists. A missing TASK-042 Timeline child yields no runnable
review, not an inferred Timeline or auto-created child.

The Python bridge exposes only typed snapshot/prepare/apply methods. Rich
application internals stay private from pywebview recursive discovery.

## 8. Security, authority, cost and failure model

- Project root symlink/non-directory or foreign Project ID: reject;
- unbound/symlinked/oversized/invalid child: reject;
- stale Product/Production/Audio/Timeline/History confirmation: consume and
  reject without write;
- caller-forged Candidate/Asset/range/fade/gain/Plan: no API accepts them;
- changed Human decision, Candidate LOCK, Asset checksum or Timeline item:
  reject or mark prior record STALE;
- concurrent apply: project lock plus Manifest CAS; deterministic duplicate is
  idempotent;
- interrupted Project save: park at TASK-043 recovery; never auto-replay;
- TASK-010 incompatibility: retain the valid Plan and visible gap; never drop
  fade/gain or claim execution readiness;
- cost: exact local deterministic compile, `estimated_cost=0`, no billable or
  Provider call;
- secrets/paths/media: absent from persisted and UI documents.

## 9. Observability and Evidence

Public projection reports logical IDs, checksums, currentness, reason codes,
record count, Project recovery state and exact false authority flags. It never
logs bodies, paths or secrets. Completion Evidence must separate:

- foundation already implemented;
- Product compilation persistence implemented;
- hosted validation;
- TASK-010/native execution not performed;
- remaining audio generation and mix gaps.

## 10. Performance

- history has a hard record maximum and document byte limit;
- snapshot projections page or truncate deterministically at a documented cap;
- one compile touches only one review/item and current bounded store documents;
- no media probing or byte hashing occurs in the UI request;
- two-hour frame values use validated integers and existing rational Timeline
  contracts.

## 11. Exact Allowed Files

Implementation may change only:

- `src/ai_video_production/audio_placement_application.py` (new);
- `src/ai_video_production/audio_placement_store.py` (new);
- `src/ai_video_production/audio_workspace_placement_binding.py` only for a
  proven strict derivation corrective;
- `src/ai_video_production/task036_shell_ui.py`;
- `src/ai_video_production/task036_trusted_launcher.py`;
- `src/ai_video_production/__init__.py`;
- `schemas/audio-placement-history.schema.json` (new);
- `src/ai_video_production/schema_resources/audio-placement-history.schema.json`
  (matching new packaged copy);
- focused new/existing TASK-026/041/042/043/036 tests;
- `CHANGELOG.md` and the exact TASK-026/current-state/roadmap/Evidence documents.

`product_project.py`, TASK-037/041/042 authoritative domain/store formats,
Provider adapters, Credential code, generation execution, TASK-010/Resolve,
Cubase, package version and Release workflows are not allowed. Any proven need
outside this list returns to Builder/Critic before editing.

## 12. Required test matrix

- strict empty legacy and exact 1.0 round-trip;
- unbound, symlinked, oversized, unknown-version, partial, duplicate and
  checksum-tampered history rejection;
- current ACCEPT + LOCK + exact Timeline proof compiles and persists;
- REVIEW/REJECT, unlocked/stale Candidate, changed Asset, missing/changed
  Timeline item, STRETCH and missing duration reject;
- caller cannot supply Candidate, Asset, range, gain/fade, Plan or authority;
- prepare/apply stale checks for all five snapshots;
- deterministic identity/idempotency and collision rejection;
- current record becomes STALE after relevant upstream change while history
  remains;
- TASK-043 child-first/Manifest-last save and pending-recovery interlock;
- restart loads exact history without replay;
- Shell allowlist, semantic action, private internal binding and visible
  non-execution boundary;
- no Provider/paid/media/TASK-010/Resolve/Cubase side effect;
- schema parity, privacy/path exclusion, focused cross-task regression, full
  Windows/WSL2 regression, compileall, JavaScript syntax and diff check;
- implementation Critic unresolved Critical/High `0 / 0`;
- hosted `9 / 9`, exact main merge and cleanup.

## 13. Implementation order

1. strict TASK-026 history model/store/schema;
2. project-scoped snapshot/currentness and recovery interlock;
3. prepare/apply re-derivation and coordinated save;
4. trusted-launch composition and narrow Shell controls;
5. security/migration/concurrency/stale/restart tests;
6. focused/full/static validation and implementation Critic;
7. Evidence/current-state/roadmap synchronization;
8. implementation PR, all-green main merge and cleanup;
9. fresh-main AUTONOMY reselection.

## 14. Release and rollback

This design selects no version, Tag or Release. Implementation is additive and
rollback is removal of the TASK-026 child binding/file through a separately
authorized Product Project revision; historical Evidence is never silently
deleted. Stable formal Release remains `v0.21.0`.
