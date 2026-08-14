# TASK-027 — R3 Generation Queue Integration Design / Review / Authorization

- Date: `2026-08-14`
- Starting Source of Truth: `main` at `57fc224560c567a71b405c3c59bce3cd881c65d7`
- Working branch: `codex/task-027-r3-generation-queue-integration`
- Owner route: `TASK-040 complete -> TASK-027 Generation Queue integration`
- DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
- Authorization: `OWNER_DIRECTED_IMPLEMENTATION_AUTHORIZED`
- Provider / paid execution in this unit: `PROHIBITED`

## Current Product audit

The checkout already contains:

- immutable Human GO / Approved Plan and exact Provider Policy identity;
- durable Approved Plan -> Scene -> TASK-037 Slot installation;
- durable TASK-013 Human Shot Feasibility Evidence;
- TASK-037 LOCK/STALE Candidate state;
- TASK-039 generation-safe Continuity resolution;
- TASK-040 immutable Prompt/Attempt Evidence;
- provider-neutral `GenerationQueueAdmissionService` and approved-plan/budget planners;
- route planning that does not itself call a Provider.

The missing Product layer is a restart-safe, user-facing queue admission record derived from those exact sources. Existing Foundation is the implementation Source of Truth and will be promoted, not recreated.

## DEV Profile re-decision

`DEV-4` is required. A false queue-ready result could cross Human GO, feasibility, continuity, locked-input, Prompt/Profile, Budget and paid-execution boundaries. The unit therefore fails closed and grants no execution authority.

## Allowed Files

- `src/ai_video_production/production_orchestrator.py`
- `src/ai_video_production/generation_queue_application.py` (new)
- `src/ai_video_production/desktop_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- focused TASK-027/TASK-036 tests;
- TASK-027 Evidence and canonical Project/roadmap/state/changelog documents.

Any other edit requires a renewed scope audit.

## Builder Design

### 1. Derived admission only

The Product Application reloads the exact current:

- Planning / Approved Plan snapshot;
- Generation Safety snapshot and current Scene feasibility record;
- Production Control snapshot;
- Continuity snapshot/recovery state;
- Prompt Registry snapshot/recovery state;
- Audit recovery state.

Callers select only an existing Prompt version. They cannot submit `plan_approved`, feasibility, required Slot IDs, Provider policy identity or a loose admission boolean.

### 2. Exact required-input proof

Every Prompt input hash must resolve uniquely to either:

- an exact Human-GO reference binding; or
- an exact LOCKED/CURRENT TASK-037 Candidate.

Missing or ambiguous hashes block admission. Locked Candidate Slot IDs are passed to the existing admission Foundation. For non-CUT continuity, the referenced START_FRAME must also have an exact TASK-039 `generation_safe` Edge.

### 3. Durable append-only queue record

`generation-queue.json` stores strict, checksum-bound, append-only admission records. Each deterministic record binds the exact Plan, Scene, target Slot, Prompt/Profile, feasibility record, input proofs, Continuity proof and all upstream snapshot hashes. CAS is serialized across local processes.

Preparation returns a one-shot Human confirmation. Apply reloads every upstream store, re-derives the record and rejects stale or replayed authority.

### 4. Execution boundary

The resulting state is `ADMISSION_READY / EXECUTION_NOT_AUTHORIZED`. It is not a Provider dispatch, paid authorization, Budget reservation, Candidate creation or generation job. Actual Provider execution remains a later exact adapter boundary.

### 5. Unified Desktop integration

Add a dedicated Generation Queue workspace with read-only admission diagnostics and explicit queue-record confirmation. It displays the exact Plan/Scene/Prompt/input/continuity proofs and states visibly that execution has not started.

## Critic Review

1. **High — raw `plan_approved=True` is caller authority.** Fix: derive exact current Approved Plan from durable Planning state.
2. **High — a caller-created feasibility object can masquerade as Evidence.** Fix: use only the current durable TASK-013 record bound to the exact Plan/Scene.
3. **High — caller-selected required Slot IDs can omit a dependency.** Fix: derive every input proof from Prompt hashes and exact GO/LOCK state.
4. **High — Prompt/Profile drift is not bound to Human GO.** Fix: require exact Prompt profile ID/version equal the Approved Provider Policy.
5. **High — LOCK alone can hide STALE or ambiguous bytes.** Fix: require exact LOCKED/CURRENT Candidate and unique asset-hash resolution.
6. **High — continuity recovery or unresolved SOFT continuity can leak into queue readiness.** Fix: require no TASK-039 recovery and generation-safe exact Edge for non-CUT input.
7. **High — TASK-038/TASK-040 pending recovery can expose inconsistent Evidence.** Fix: block queue preparation/apply while either recovery is pending.
8. **High — in-memory readiness disappears at restart and can be replayed.** Fix: strict append-only CAS queue store and deterministic identity.
9. **High — snapshot changes between prepare/apply can broaden authority.** Fix: reload and re-derive every bound identity at apply.
10. **High — Queue UI can be mistaken for generation execution.** Fix: no dispatch command and invariant false execution/paid/Candidate flags.

Unresolved Critical/High after Builder correction: `0 / 0`.

## Final Plan / Judge Decision

`PASS / IMPLEMENTATION AUTHORIZED`

Implementation order:

1. harden admission result diagnostics and tests;
2. implement durable project Queue Application and exact input/continuity derivation;
3. integrate the allowlisted Desktop Generation Queue workspace;
4. run focused/full/compile/JavaScript/diff gates;
5. publish PR, require all hosted checks, exact merge and separate closure.

No package, Tag or GitHub Release is selected at kickoff.
