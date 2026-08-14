# TASK-040 — R3 Prompt Evidence Product Promotion Design / Review / Authorization

- Date: `2026-08-14`
- Starting Source of Truth: `main` at `90998626642cd179c73027a9c4c1f8370a623c43`
- Working branch: `codex/task-040-r3-prompt-evidence-product-promotion`
- Owner route: `TASK-039 complete -> TASK-040 Prompt Registry / Generation Evidence`
- DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
- Authorization: `OWNER_DIRECTED_IMPLEMENTATION_AUTHORIZED`
- Provider / paid execution: `PROHIBITED_IN_THIS_UNIT`

## Current Product audit

The current checkout already contains:

- append-only Prompt ID/version, body hash/reference, Provider Profile, input hashes and Keep Conditions;
- Generation Attempt Prompt/Slot/input/profile/parent integrity checks;
- checksum/CAS protected body-free, credential-free Prompt/Attempt persistence;
- PASS Attempt -> exact TASK-037 Candidate GENERATED_FROM binding;
- Human NEEDS_REGENERATION + Audit-bound adaptive strategy planning;
- immutable next Prompt-version draft with stale-lineage and Provider-switch controls;
- automated Foundation/schema tests.

The Product gaps are strict restart parsing, cross-process publication, durable project Application/recovery, exact lineage order and a user-facing Prompt Evidence workspace.

## Registry / route decision

Task identity remains `TASK-040`. The next owner after hosted closure is the TASK-027 Generation Queue integration slice on its own branch. TASK-040 records Prompt/Generation Evidence and Human regeneration intent; it does not execute or authorize generation.

## DEV Profile re-decision

`DEV-4` is required because PASS Generation Evidence changes both Prompt authority and TASK-037 Candidate lineage. Partial publication, normalized/tampered recovery or incorrect attempt order could make an untraceable Candidate appear safe for downstream work.

## Allowed Files

- `src/ai_video_production/prompt_registry.py`
- `src/ai_video_production/prompt_registry_store.py`
- `src/ai_video_production/generation_output_binding.py`
- `src/ai_video_production/regeneration_planning.py`
- `src/ai_video_production/regeneration_prompt_draft.py`
- `src/ai_video_production/prompt_evidence_application.py` (new)
- `src/ai_video_production/desktop_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- TASK-040/TASK-036 focused tests and the TASK-040 schema;
- TASK-040 Evidence and canonical Project/roadmap/state/changelog documents required for the Gate.

Any change outside this list requires re-audit before editing.

## Builder Design

### 1. Registry/store hardening

- reject unknown or normalized fields and ambiguous scalar coercion during restart;
- reserialize recovered domain state and require its exact snapshot hash;
- serialize Prompt compare-and-swap check plus replace across local processes;
- require exact Provider Profile version and unique output Candidate ownership;
- preserve non-decreasing same-Slot parent lineage and use parent links, not dictionary insertion order, for failure streaks.

### 2. Durable project Application

Use fixed project-owned files:

- `prompt-registry.json`;
- shared TASK-037 `production-control.json`;
- shared TASK-038 `candidate-audit.json`;
- `task040-attempt-transaction.json`.

Every command reloads exact snapshots and verifies project/Scene/Slot scope. Initial Prompt registration, Generation Evidence import and regeneration Prompt registration use separate one-shot Human confirmations.

A PASS Evidence import must name an already registered exact Candidate and is a prepared recoverable two-store transaction across Prompt Registry and Production Control. FAIL/CANCELLED/HUMAN_REQUIRED Evidence changes only Prompt Registry. It never launches a Provider or creates a Candidate.

### 3. Regeneration routing

- compile only from exact Candidate bytes plus the durable Human NEEDS_REGENERATION/Audit decision;
- traverse explicit parent Attempt lineage for repeated structural Failure Codes;
- bind the draft to exact Prompt/Production/Audit snapshots;
- require a new immutable Prompt version and reject stale replay;
- allow Provider Profile change only at PROVIDER_SWITCH or higher;
- registration still grants no paid or Provider authority.

### 4. User-facing Prompt Evidence workspace

Add allowlisted `PROMPT_EVIDENCE` Desktop workspace commands and a `Prompt証跡` drawer. It displays Prompt versions, Provider Profile identity, input hashes, Keep Conditions, Attempt parent/output/result/failure/cost/latency metadata and recovery state. Registration/import/regeneration are explicit separate actions and all UI language states that no Provider or Candidate creation occurs.

## Critic Review

1. **High — Prompt CAS check and replace are not cross-process serialized.** Fix: shared project-local exclusive lock.
2. **High — checksum-valid unknown/normalized fields can survive parser coercion.** Fix: exact document/row types and domain reserialization hash.
3. **High — PASS Attempt publication spans Prompt and Production stores without recovery.** Fix: exact prepared transaction and bounded restart recovery.
4. **High — insertion order is not durable attempt chronology.** Fix: parent-lineage traversal for repeated-failure streaks.
5. **High — missing Provider Profile version bypasses exact Prompt policy binding.** Fix: exact non-null match.
6. **High — one Candidate can be claimed by multiple PASS Attempts.** Fix: unique output Candidate lineage.
7. **High — arbitrary loose Prompt scope can detach Evidence from project Production.** Fix: exact existing project Slot/Scene and private body reference.
8. **High — regeneration draft service can be called with an invented plan.** Fix: Product Application derives the plan from durable Audit/Production/Prompt state and snapshot-binds confirmation.
9. **High — recovery-pending state could expose normal mutation actions.** Fix: fail closed and suppress all actions until exact recovery.
10. **High — UI Evidence import could be mistaken for Provider execution.** Fix: explicit import-only wording and invariant false execution/creation flags.

Unresolved Critical/High after Builder Design correction: `0 / 0`.

## Final Plan / Judge Decision

`PASS / IMPLEMENTATION AUTHORIZED`

Implementation order:

1. harden Prompt domain/store and lineage tests;
2. implement durable project Application, PASS two-store recovery and regeneration confirmation;
3. wire allowlisted Desktop Prompt Evidence workspace;
4. run focused Critic gate, full regression, Windows/WSL2 compile, JavaScript and diff gates;
5. publish implementation PR, require all hosted checks, merge exactly, then record closure on a separate branch.

No package, Tag or GitHub Release is selected by this kickoff decision.
