# TASK-039 — R3 Continuity Product Promotion Local Closure Evidence

- Date: `2026-08-14`
- Starting Source of Truth: `main` at `0ef7bfde85783f3f73c502c03ab5fce72c2a52c9`
- Working branch: `codex/task-039-r3-continuity-product-promotion`
- DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
- Local Gate: `PASS`
- Hosted PR Gate: `PENDING`
- Release decision: `NO_RELEASE_AT_TASK039_R3_CHECKPOINT`

## Promoted Product capability

- a durable project-scoped TASK-039 Application joins Continuity Registry and TASK-037 Production Control without inventing a second source of truth;
- Edge registration is derived from the exact locked END_FRAME Candidate and the existing START_FRAME Slot, then protected by exact old/new snapshot identities and one-shot Human confirmation;
- a checksum-bound prepared transaction makes partial two-store publication visible and restart-recoverable instead of silently claiming continuity safety;
- exact OLD/OLD, CONTINUITY_NEW/PRODUCTION_OLD, CONTINUITY_OLD/PRODUCTION_NEW and NEW/NEW states expose only bounded recovery actions; unknown mixtures fail closed;
- target inspection derives the exact current locked Candidate; callers cannot submit loose Asset bytes;
- immutable Edge inspection preserves prior Evidence; a changed target requires a new Edge identity;
- DIRECT_CONTINUATION requires exact Asset ID and SHA-256 and cannot be Human-overridden;
- only an inspected SOFT_CONTINUITY result can receive a separate one-shot Human approval;
- explicit STALE propagation includes the changed root and all deterministic downstream dependencies while retaining trace identities and prior resolutions;
- the unified Desktop Shell exposes a dedicated `連続性` workspace for registration, inspection, soft approval, STALE propagation and bounded recovery;
- no operation regenerates, physically deletes, calls a Provider, spends credits or mutates Resolve/Cubase.

## Final Critic Review

The pre-implementation High findings were corrected. Final review additionally hardened:

1. exact transaction top-level fields, checksum/hash formats and nested Edge shape so checksum-valid unknown authority fields are rejected;
2. strict Shell request types so booleans or arbitrary objects cannot be silently coerced into valid-looking IDs;
3. cross-process Continuity compare-and-swap serialization and duplicate resolution recovery rejection;
4. consumed-before-revalidation Human tokens;
5. exact two-store crash states and generation-safe suppression while recovery is pending;
6. immutable production-derived target inspection;
7. coherent LOCKED/STALE Slot-Candidate persistence and changed-root propagation;
8. shared trusted-launch Production Control identity between TASK-037 and TASK-039.

Unresolved Critical/High: `0 / 0`.

## Validation

- final full regression in Ubuntu WSL2 `/mnt/d`: `869 / 869 PASS`;
- focused TASK-039/TASK-037/TASK-036 Application, Store, Shell and launcher integration: `88 / 88 PASS`;
- Windows Python `compileall` with isolated temporary bytecode cache: PASS;
- Ubuntu WSL2 Python `compileall` with isolated temporary bytecode cache: PASS;
- Desktop HTML JavaScript extraction and Node.js syntax check: PASS;
- `git diff --check`: PASS.

The WSL test environment was created only in `/tmp` and installed the repository's free declared development dependencies. It did not alter the repository, run a paid Provider or perform product generation. The existing Windows `.venv` launcher points to a removed Python installation, so Windows compile used the Codex-bundled Python and an isolated temporary cache without deleting the historical cache.

## Authority and release boundary

This unit does not claim the complete R3 high-cost admission conjunction. TASK-040 Prompt Registry / Generation Evidence and the TASK-027 Generation Queue integration slice remain later owners. Continuity PASS or Human-approved SOFT continuity does not itself authorize Provider execution.

No image/video/audio Provider, paid call, credit purchase, Budget reservation, Candidate generation, automatic Human decision, Resolve/Cubase mutation, production media write or publishing occurred. Existing untracked raw native `evidence/` is preserved and excluded from staging.

Formal closure requires a dedicated PR, all hosted checks, exact `main` merge verification and branch cleanup. Stable Product release remains `v0.20.1`; no package, annotated Tag or GitHub Release is selected at this checkpoint.
