# TASK-037 — R2 Product Promotion Design, Review and Authorization

- Date: `2026-08-14`
- Starting implementation Source of Truth: `main` at `7873488c85cf1fd9e49b8061e4c201b6fec976d6`
- Working branch: `codex/task-037-r2-product-promotion`
- Governance route: `OWNER_DIRECTED_R2_PRODUCT_PROMOTION`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Decision: `IMPLEMENTATION_AUTHORIZED`

## Current OS audit and Registry check

BAI Development OS TASK-018 is complete and OS `v1.1.0` remains published. PR #25 added the append-only BAI VIDEO PRODUCTION `v0.20.1` Consumer supplement without reopening TASK-018; TASK-017 remains paused and Production Activation remains `BLOCKED`.

The Consumer checkout is newer than every supplied handoff package and is the implementation Source of Truth. Local `main` and `origin/main` both resolve to `7873488c85cf1fd9e49b8061e4c201b6fec976d6`. Existing untracked native `evidence/` directories are preserved and excluded from staging.

`PROJECT.md`, `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md` and Roadmap Ver.1.15 agree that TASK-036/M3B and `v0.20.1` are complete and that the next Owner-routed Product wave is R2:

1. TASK-037 Asset Registry 2 / Scene Asset Slot;
2. TASK-038 Audit Workspace / Candidate Quality Loop;
3. TASK-027 Planning Workspace minimum / Scene Contract.

## Existing Foundation audit

TASK-037 is not a greenfield implementation. Current `main` already contains:

- Scene Asset Slot, immutable Candidate versions, LOCK/STALE and dependency graph domain rules;
- deterministic transitive stale propagation and locked-asset trace;
- crash-safe checksummed snapshot persistence with exact compare-and-swap replacement;
- approved Plan -> Scene -> Slot trace and cross-store bundle validation/recovery;
- TASK-038 Audit and Human-decision bindings;
- TASK-027 Planning, bundle and read-only Production Dashboard projections;
- a read-only TASK-036 Production Control workspace projection.

Focused TASK-027/037/038 validation passed `102 / 102`. The missing product layer is a durable TASK-037 Application Service and a bounded user-facing Production Control command surface. Existing Foundation must be promoted, not duplicated.

## DEV Profile re-evaluation

`DEV-4 FOUNDATION CRITICAL` remains required because this unit changes durable Plan-to-Asset relationship state, optimistic concurrency, Human lock authority and the future cross-workspace source of truth. A false lock, stale overwrite or cross-project mutation could invalidate downstream generation and editing decisions.

Safety floors:

- no media-byte ownership or physical deletion;
- no paid Provider execution;
- no automatic regeneration;
- no Resolve/Cubase mutation;
- no AI score becoming Human authority;
- exact project, snapshot, Slot revision, Candidate bytes and one-shot confirmation binding;
- unknown or conflicting state fails closed.

## Allowed Files

- `src/ai_video_production/production_control_application.py`
- `src/ai_video_production/production_control_store.py`
- `src/ai_video_production/task037_production_workspace.py`
- `src/ai_video_production/desktop_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- focused TASK-037, Production Control Store and Shell tests under `tests/`
- TASK-037 Product documents and Product state/roadmap/task index files
- `CHANGELOG.md` only for the required unreleased Product-change record; package/version fields remain unchanged
- `.github/workflows/ci.yml` only if hosted validation exposes an infrastructure blocker that prevents the authorized matrix from reaching Product tests

Release metadata, native Resolve/Cubase projects, raw `evidence/`, paid Provider adapters and BAI Development OS runtime files are not allowed in this implementation unit.

## Builder Design

### Phase A — durable Application Service

- Open only a fixed project-owned Production Control snapshot path.
- For every durable command, reload the current snapshot and bind the command to its exact snapshot checksum.
- Install Slots only from an existing Human-approved Plan and append Candidates without overwriting prior Candidate versions.
- Prepare and apply Candidate locks through a one-shot confirmation bound to project, Slot revision, Candidate ID and Asset checksum.
- Require the Candidate to have reached `ACCEPTED` through the existing TASK-038 Human-decision binding before a lock can be applied.
- Persist through the existing atomic writer and exact compare-and-swap contract.
- Return a deterministic projection; never embed host paths or media bytes.

### Phase B — Product Workspace command surface

- Add `PRODUCTION_CONTROL` as an explicit Shell workspace without displacing Viewer/Timeline as the primary editing canvas.
- Expose only allowlisted local commands for Candidate registration, audit-ready transition and confirmed lock. Slot installation remains bound to the existing TASK-027 Human-approved Plan service; loose Slot creation is not exposed.
- Display Slot/Candidate history, LOCK/STALE, exact attention reasons and recovery errors.
- Keep Audit decision ownership in TASK-038; do not invent an accept/reject shortcut in TASK-037.

### Phase C — validation and closure

- Add concurrency, replay, stale-confirmation, tamper, crash-safe persistence and cross-project rejection tests.
- Run focused R2 tests, full regression, compileall and hosted CI.
- Close TASK-037 only when the durable trace is user-operable without terminal/JSON and no Critical/High finding remains.

## Critic Review

One bounded pre-implementation Critic review was performed.

- Critical/High findings after correction: `0 / 0`.
- Corrected design risk: mutating a long-lived in-memory Registry before a failed save could leave memory ahead of disk. Resolution: each durable command reloads the exact persisted snapshot, mutates an isolated Registry and publishes only after CAS save succeeds.
- Corrected authority risk: TASK-037 could accidentally accept a Candidate while locking it. Resolution: acceptance remains TASK-038 ownership; TASK-037 lock requires an already `ACCEPTED` Candidate and exact one-shot Human confirmation.
- Corrected concurrency risk: a confirmation bound only to Slot revision could miss changed Candidate bytes. Resolution: bind snapshot checksum, Slot revision, Candidate identity and `asset_sha256`.
- Corrected cross-process CAS risk: an existence/checksum check outside the atomic replacement could allow two first writers to pass concurrently. Resolution: serialize the Production Control CAS check and atomic replacement with a project-local cross-platform file lock.
- Corrected replay risk: a stale apply attempt could leave its confirmation reusable. Resolution: consume the one-shot confirmation before reloading and validating current state.
- Corrected product-boundary risk: broad Shell wiring could couple R2 to Resolve. Resolution: the first command surface is local relationship metadata only; Provider/NLE execution flags remain false.

## Final Plan

1. implement Phase A service/projection and focused tests;
2. run the bounded Critic gate and correct only concrete findings;
3. implement Phase B Shell integration using the accepted service boundary;
4. run focused plus full regression and compileall;
5. record TASK-037 closure Evidence;
6. push only this dedicated branch, open a PR, require all-green checks, merge to `main`, verify exact SHA and delete the branch;
7. create a new dedicated branch for TASK-038.

The Owner's post-TASK-036 handoff and instruction to continue authorize this R2 TASK-037 plan. They do not authorize paid generation, external NLE mutation, physical deletion, direct push to `main`, force push or claims beyond accepted Evidence.
