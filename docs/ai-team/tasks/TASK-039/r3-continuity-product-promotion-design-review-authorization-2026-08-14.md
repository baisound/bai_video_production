# TASK-039 — R3 Continuity Product Promotion Design / Review / Authorization

- Date: `2026-08-14`
- Starting Source of Truth: `main` at `0ef7bfde85783f3f73c502c03ab5fce72c2a52c9`
- Working branch: `codex/task-039-r3-continuity-product-promotion`
- Owner route: `TASK-013 complete -> TASK-039 Continuity Map / STALE propagation`
- DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
- Authorization: `OWNER_DIRECTED_IMPLEMENTATION_AUTHORIZED`
- Provider / paid execution: `PROHIBITED_IN_THIS_UNIT`

## Current Product audit

The current checkout already contains:

- immutable Continuity Edge contracts for `DIRECT_CONTINUATION`, `SOFT_CONTINUITY` and `DISCONTINUOUS`;
- exact source Candidate/Asset SHA-256 binding;
- target validation and fail-closed generation-safe checks;
- non-overridable DIRECT_CONTINUATION identity;
- explicit Human SOFT_CONTINUITY approval;
- Continuity -> TASK-037 dependency binding, cycle rejection and transitive STALE propagation;
- checksum/CAS/symlink/size protected registry persistence;
- automated Foundation tests and schema.

The Product gaps are a durable project Application joining Continuity and Production snapshots, recoverable two-store Edge registration, local process serialization, restart-safe Human approval and a user-facing Continuity workspace.

## Registry / route decision

Task identity remains `TASK-039`. TASK-040 follows only after TASK-039 hosted closure. TASK-039 does not generate or delete Assets, clear Human Audit decisions, or weaken exact identity.

## DEV Profile re-decision

`DEV-4` is required because an Edge registration changes both the Continuity authority and TASK-037 stale dependency graph. A partial/crashed write could otherwise make downstream generation appear safe or leave stale propagation disconnected.

## Allowed Files

- `src/ai_video_production/continuity_registry_store.py`
- `src/ai_video_production/production_control_store.py`
- `src/ai_video_production/production_control.py`
- `src/ai_video_production/continuity_workspace.py`
- `src/ai_video_production/continuity_application.py` (new)
- `src/ai_video_production/desktop_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- `tests/test_task039_continuity_registry_store.py`
- `tests/test_task037_production_control_store.py`
- `tests/test_task037_production_control.py`
- `tests/test_task039_continuity_workspace.py`
- `tests/test_task039_continuity_application.py` (new)
- `tests/test_task036_desktop_shell.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_trusted_launcher.py`
- TASK-039 Evidence and canonical Project/roadmap/state/changelog documents required for the Gate.

Any change outside this list requires re-audit before editing.

## Builder Design

### 1. Store and one-shot hardening

- serialize Continuity CAS check + replace across local processes;
- reject duplicate or normalized-away resolution identities during recovery;
- consume SOFT approval tokens before any current-state revalidation;
- preserve exact target Candidate/Asset SHA binding.

### 2. Durable project Application

Use fixed project-owned files:

- `production-control.json`;
- `continuity-registry.json`;
- `task039-edge-transaction.json`.

Every command reloads current snapshots and verifies project scope. Edge registration is a two-step one-shot Human operation derived from the exact locked source Candidate and existing target Slot. The Application prepares exact old/new Continuity and Production hashes before either store changes, then saves both and commits the transaction.

On restart, `OLD/OLD`, `CONTINUITY_NEW/PRODUCTION_OLD`, `CONTINUITY_OLD/PRODUCTION_NEW` and `NEW/NEW` states expose only exact COMPLETE/ABANDON/FINALIZE recovery actions. Unknown mixtures remain blocked.

### 3. Inspection, Human review and STALE

- target inspection derives the exact currently locked target Candidate; caller-provided loose bytes are prohibited;
- an immutable Edge receives one current inspection; target change requires a new Edge identity rather than silently erasing Human Evidence;
- only inspected SOFT_CONTINUITY can receive one-shot Human approval;
- DIRECT_CONTINUATION mismatch cannot be Human-overridden;
- explicit upstream STALE propagation reuses TASK-037 deterministic graph traversal and never regenerates or deletes media.

### 4. User-facing Continuity workspace

Add allowlisted `CONTINUITY` Desktop workspace commands and a `連続性` drawer. It displays exact source/target identity, boundary type, machine/Human resolution, generation-safe state, locked/STALENESS and root cause. Edge registration, inspection, soft approval and transaction recovery are explicit separate actions.

## Critic Review

1. **High — Continuity CAS check and replace are not serialized across processes.** Fix required: project-local exclusive lock.
2. **High — SOFT confirmation is consumed only after validation.** Fix required: consume before revalidation so a failed stale token can never become valid later.
3. **High — Edge registration spans two stores without recovery.** Fix required: exact prepared transaction and restart recovery.
4. **High — loose target Asset input can detach inspection from Production.** Fix required: derive only from exact locked target Candidate.
5. **High — reinspection can overwrite Human approval Evidence.** Fix required: immutable Edge inspection at Product layer; new target requires new Edge.
6. **High — user-facing state could imply continuity PASS while transaction recovery is pending.** Fix required: disable all mutation/approval actions during recovery and make generation-safe false.
7. **High — accepted STALE propagation cannot round-trip through the Production Store because the historical parser requires a traced locked Candidate to remain LOCKED even when both Slot/Candidate are correctly STALE.** Fix required: validate LOCKED and STALE trace pairs against their respective lifecycle states.
8. **High — propagating from a locked source Slot starts at dependents and can stale its Candidate while leaving the source Slot LOCKED.** Fix required: TASK-039 explicitly includes the changed root Slot in propagation so its Slot/Candidate trace remains coherent; existing callers retain the historical default.

Unresolved Critical/High after Builder Design correction: `0 / 0`.

## Final Plan / Judge Decision

`PASS / IMPLEMENTATION AUTHORIZED`

Implementation order:

1. harden store and one-shot confirmation;
2. implement durable two-store Application/recovery and tests;
3. wire allowlisted Desktop Continuity workspace;
4. run focused Critic gate, Windows full regression, compile/diff/JavaScript and WSL2 compile gates;
5. publish implementation PR, require all hosted checks, merge exactly, then record closure on a separate branch.

No package, Tag or GitHub Release is selected by this kickoff decision.
