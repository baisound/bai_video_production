# TASK-013 — R3 Generation Safety Product Promotion Design / Review / Authorization

- Date: `2026-08-14`
- Starting Source of Truth: `main` at `cc893ee064f8935334dc0c5202a17d244577540a`
- Working branch: `codex/task-013-r3-feasibility-product-promotion`
- Owner route: `R3 current-state audit -> TASK-013 Shot Feasibility / Visual Compliance`
- DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
- Authorization: `OWNER_DIRECTED_IMPLEMENTATION_AUTHORIZED`
- Provider / paid execution: `PROHIBITED_IN_THIS_UNIT`

## Current OS / Product audit

R2 is complete through TASK-037, TASK-038 and the bounded TASK-027 Planning Workspace minimum. The current checkout already contains more TASK-013 Foundation than the historical design status suggests:

- deterministic Scene-Compatible Reference / Shot Feasibility contracts;
- exact DIRECT_CONTINUATION Asset ID and SHA-256 checks;
- provider-neutral creative-generation admission planners;
- Visual Compliance Contract, weighted diagnostic scoring and fail-closed decision;
- repeated structural Failure Code escalation;
- Visual Compliance -> immutable TASK-038 Audit -> TASK-037 Candidate lifecycle binding;
- tests proving Visual PASS is not Human ACCEPT and Visual FAIL is not automatic Human REJECT/regeneration.

The missing Product layer is durable project-scoped feasibility state, exact binding to the current Human-approved Plan, the Promotion addendum checks, and a user-facing review route. Provider execution is not necessary to close this unit.

## Registry / route decision

TASK identity remains `TASK-013`. No task is renumbered. The R3 order is:

1. TASK-013 Shot Feasibility / Visual Compliance Product promotion;
2. TASK-039 Continuity Map / STALE propagation;
3. TASK-040 Prompt Registry / Generation Evidence;
4. TASK-027 Generation Queue integration.

TASK-013 produces truthful `FEASIBILITY_PASS` Evidence but does not claim the complete high-cost admission conjunction until later owners provide `REQUIRED_INPUT_LOCKED` and queue integration.

## DEV Profile re-decision

`DEV-4` is required because the change joins Human Final Authority, Approved Plan identity, project persistence and generation admission. A stale or cross-project PASS could incorrectly admit expensive work later.

## Allowed Files

- `src/ai_video_production/shot_feasibility.py`
- `src/ai_video_production/generation_safety_application.py` (new)
- `src/ai_video_production/desktop_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- `tests/test_task013_shot_feasibility.py`
- `tests/test_task013_creative_generation.py`
- `tests/test_task013_approved_creative_generation.py`
- `tests/test_task027_approved_plan_orchestration.py`
- `tests/test_task027_production_orchestrator.py`
- `tests/test_task013_generation_safety_application.py` (new)
- `tests/test_task036_desktop_shell.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_trusted_launcher.py`
- TASK-013 Evidence and canonical Project/roadmap/state/changelog documents required for the Gate.

Any change outside this list requires re-audit before editing.

## Builder Design

### 1. Contract hardening

Promote the addendum checks into the canonical assessment:

- `task_axis_valid`;
- `depth_order_valid`;
- `occlusion_valid`;
- `furniture_integrity_valid`;
- `room_anchor_integrity_valid`;
- `production_gear_absent`;
- `character_identity_valid`.

The complete exact check set is required. Deterministic contract FAIL cannot be overridden by Human input. An assessment receives a deterministic SHA-256 identity.

### 2. Durable project application

Create a project-owned `generation-safety.json` Application state. Every operation reloads current Planning and safety snapshots, validates project/Approved Plan/Blueprint/Scene identity, uses exact optimistic checks and publishes atomically under a cross-process lock.

Human feasibility PASS is a two-step one-shot operation:

1. prepare against exact Planning + safety snapshots;
2. apply with reviewer identity after reloading and revalidating all state.

A newer Proposal/Plan, changed input, replayed token, foreign project or unknown Scene fails closed. A Plan change makes the prior assessment visible as stale but never current PASS.

### 3. User-facing Generation Safety workspace

Add an allowlisted `GENERATION_SAFETY` workspace to the existing Desktop Shell. It displays every current Approved Plan Scene, reference roles, required visible elements, camera/orientation, prohibited changes, all structural checks, blocking reasons and status.

The Human review action requires explicit PASS/FAIL for every non-deterministic check and a second confirmation before durable publication. It starts no Provider, paid operation, Budget reservation, Candidate creation, Resolve/Cubase mutation or publishing.

### 4. Visual Compliance boundary

Retain the already-implemented structured Visual Compliance -> TASK-038 Audit path. The Generation Safety projection states that generated Candidate acceptance remains in TASK-038. This unit does not fabricate image observations, execute a Vision provider, or convert Visual PASS into Human ACCEPT.

## Critic Review

### Critical / High findings before implementation

1. **High — historical assessment check set omits Promotion addendum controls.** Required fix: extend the exact canonical set and tests.
2. **High — in-memory assessment can be detached from the current Approved Plan after restart/change.** Required fix: persist exact Plan/Blueprint/Planning snapshot identities and classify mismatches stale.
3. **High — a single-call Human PASS would be replayable or race-prone.** Required fix: exact one-shot prepare/apply, consume before revalidation, cross-process serialization and CAS.
4. **High — UI or callers could claim generation readiness from a partial check map.** Required fix: require the complete exact check set; missing/unknown fields fail.
5. **High — Visual Compliance could be mistaken for Human Final Authority.** Required fix: preserve TASK-038 decision ownership and expose explicit non-claim fields.

Unresolved Critical/High after Builder Design correction: `0 / 0`.

Post-implementation Critic also verified the stored nested checksums, append-only revision identity, derived assessment status, multi-Proposal ambiguity handling and durable TASK-038 Audit scope. Final unresolved Critical/High remains `0 / 0`.

## Final Plan / Judge Decision

`PASS / IMPLEMENTATION AUTHORIZED`

Implementation order:

1. harden assessment contracts and deterministic identity;
2. implement durable exact Plan-bound Application and concurrency/restart tests;
3. wire allowlisted Shell bridge and Generation Safety workspace;
4. run focused Critic gate, full Windows regression, compile/diff gates and WSL2 compile gate;
5. publish implementation PR, require all hosted checks, merge exactly, then record closure on a separate branch.

No package, Tag or GitHub Release is selected by this kickoff decision. Exact release finalization is deferred until the complete selected Product release unit is known.
