# TASK-040 — R3 Prompt Evidence Product Promotion Local Closure Evidence

- Date: `2026-08-14`
- Starting Source of Truth: `main` at `90998626642cd179c73027a9c4c1f8370a623c43`
- Working branch: `codex/task-040-r3-prompt-evidence-product-promotion`
- DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
- Local Gate: `PASS`
- Hosted PR Gate: `PENDING`
- Release decision: `NO_RELEASE_AT_TASK040_R3_CHECKPOINT`

## Promoted Product capability

- immutable Prompt identity/version, private body reference/hash, Provider Profile version, input hashes and Keep Conditions are now durable Product Evidence;
- completed Generation Attempt Evidence is imported without starting a Provider, spending credits or creating a Candidate;
- PASS output Evidence binds one exact existing TASK-037 Candidate to one exact Attempt;
- PASS Prompt/Production publication uses a checksum-bound prepared transaction with exact bounded restart recovery;
- FAIL/CANCELLED/HUMAN_REQUIRED imports update only Prompt Evidence;
- exact project/Scene/Slot scope, Provider Profile version, input identity and non-decreasing parent strategy lineage fail closed;
- repeated structural failures follow explicit parent links rather than persistence order;
- only durable TASK-038 Human `NEEDS_REGENERATION` authority can prepare the next immutable Prompt version;
- regeneration preparation and apply both require stable Prompt/Production/Audit snapshots and no pending TASK-038/TASK-040 recovery;
- the unified Desktop Shell exposes a dedicated Prompt Evidence workspace for metadata registration, completed-attempt import, Human-routed next Prompt registration and bounded recovery;
- no operation calls a Provider, authorizes paid execution, creates media/Candidates, mutates Resolve/Cubase or starts the later Generation Queue.

## Final Critic Review

The pre-implementation High findings were corrected. Final review additionally hardened:

1. exact top-level and nested persistence fields, strict scalar types and domain reserialization checksum;
2. cross-process serialized Prompt compare-and-swap;
3. non-empty transaction/project identity and checksum-valid unknown-field rejection;
4. exact Provider Profile version and unique output Candidate ownership;
5. parent-lineage strategy non-regression and durable failure-streak ordering;
6. ProductError normalization for invalid external metadata;
7. TASK-038 recovery interlock and exact Audit/Production snapshot revalidation at regeneration prepare and apply;
8. UI regeneration action visibility only for durable Human `NEEDS_REGENERATION` decisions;
9. one-shot confirmations consumed before stale revalidation;
10. shared trusted-launch TASK-037/TASK-038 identity and import-only execution boundaries.

Unresolved Critical/High: `0 / 0`.

## Validation

- final full regression in Ubuntu WSL2 `/mnt/d`: `885 / 885 PASS`;
- focused TASK-040 domain/store/Application and TASK-036 Shell/launcher integration: `84 / 84 PASS`;
- Windows Python `compileall` with isolated temporary bytecode cache: PASS;
- Ubuntu WSL2 Python `compileall` with isolated temporary bytecode cache: PASS;
- Desktop HTML JavaScript extraction and Node.js syntax check: PASS;
- `git diff --check`: PASS.

The test environments used only free declared development dependencies. They did not alter Product projects, call a paid Provider or perform generation. Existing untracked raw native `evidence/` remains preserved and excluded from staging.

## Authority and release boundary

TASK-040 records Evidence and creates a next immutable Prompt version after an exact Human regeneration decision. It does not complete TASK-027 Generation Queue integration and does not claim the final high-cost admission conjunction or Provider execution authority.

Formal closure requires a dedicated PR, all hosted checks, exact `main` merge verification and branch cleanup. Stable Product release remains `v0.20.1`; no package, annotated Tag or GitHub Release is selected at this checkpoint.
