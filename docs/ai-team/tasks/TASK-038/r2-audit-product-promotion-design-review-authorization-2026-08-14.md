# TASK-038 — R2 Audit Product Promotion Design, Review and Authorization

- Date: `2026-08-14`
- Starting implementation Source of Truth: `main` at `66446cf01ad5210ce196bc2803a5ffb18a37139c`
- Working branch: `codex/task-038-audit-product-promotion`
- Governance route: `OWNER_DIRECTED_R2_PRODUCT_PROMOTION`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Decision: `IMPLEMENTATION_AUTHORIZED`

## Current audit and Registry check

TASK-037 is formally complete. PR #24 and closure PR #25 each passed `9 / 9`; the exact closure main SHA is `66446cf01ad5210ce196bc2803a5ffb18a37139c`. Stable release remains `v0.20.1`; no TASK-037 Tag/Release was selected. Existing untracked raw native Evidence is preserved and excluded.

The canonical R2 order now activates TASK-038, followed by TASK-027 Planning Workspace minimum after this Gate.

## Existing Foundation audit

TASK-038 is not greenfield. Current main already contains:

- immutable AI/Human Audit records, dimensions, findings, Failure Codes and alternate-use proposals;
- checksummed `candidate-audit.json` persistence with CAS and tamper/reference validation;
- AI score separated from Human authority;
- one-shot ACCEPT / REJECT / ALTERNATE_USE / NEEDS_REGENERATION confirmation;
- exact Candidate Asset SHA and Audit-set binding;
- TASK-038 -> TASK-037 lifecycle binding;
- cross-store validation and locked Production trace.

Focused pre-kickoff validation passed `42 / 42`. Missing Product layers are a durable project-scoped two-store Application Service, explicit interrupted-decision recovery and a user-facing Audit surface in the existing Production Control drawer.

## DEV Profile re-evaluation

`DEV-4 FOUNDATION CRITICAL` is required because a Human decision changes durable Candidate lifecycle across Audit and Production Control stores. A partial update could display one decision while locking authority observes another state.

Safety floors:

- AI score or finding never applies a decision;
- Reject is not Delete;
- NEEDS_REGENERATION never starts a Provider;
- exact project, Production snapshot, Audit snapshot, Candidate bytes, Audit set and one-shot confirmation binding;
- interrupted cross-store writes fail closed and require an explicit recovery command;
- recovery may only complete the exact prepared transition, never infer a different decision;
- no media-byte write, paid Provider, Resolve/Cubase mutation or automatic regeneration.

## Allowed Files

- `src/ai_video_production/audit_application.py`
- `src/ai_video_production/audit_workspace.py`
- `src/ai_video_production/candidate_audit_store.py`
- `src/ai_video_production/production_control_store.py` only if shared local transaction-lock reuse is required
- `src/ai_video_production/desktop_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- focused TASK-038, TASK-037 and Shell tests under `tests/`
- TASK-038 documents and canonical Product state/roadmap/task index
- `CHANGELOG.md` for the required Unreleased entry

Package/version metadata, native NLE projects, raw `evidence/`, Provider adapters and BAI Development OS runtime files are outside this unit.

## Builder Design

### Phase A — durable Audit Application

- use fixed project-owned `production-control.json`, `candidate-audit.json` and a bounded TASK-038 decision-transaction record;
- reload both current stores for every durable operation and validate exact project/Candidate/Audit identity;
- accept immutable Audit records only against an existing exact Candidate and without applying Human authority;
- prepare Human decisions against exact Production/Audit snapshot hashes and Candidate/Audit bytes;
- write a prepared transaction before the two-store decision update;
- publish Audit decision first and Production lifecycle second under one project-local lock;
- mark the transaction committed only after both stores match the exact prepared result;
- expose explicit fail-closed recovery for old/old, audit-new/production-old and new/new states; unknown mixtures remain blocked.

### Phase B — user-facing Audit workspace

- extend the existing `制作管理` drawer rather than create a second application;
- show Candidate version/history, AI versus Human auditor identity, dimensions, findings, Failure Codes, critical state and alternate-use proposals;
- expose ACCEPT / REJECT / ALTERNATE_USE / NEEDS_REGENERATION only when the durable Application Service reports them;
- show Candidate ID, Asset SHA, Audit refs, critical state and selected decision in the Human confirmation;
- require an explicit actor identity and optional bounded notes; no hidden default decision;
- after ACCEPT, TASK-037 may offer its separate LOCK confirmation; decision and lock remain distinct actions.

### Phase C — validation and closure

- test CAS conflicts, stale/replayed confirmation, crash after Audit save, exact recovery, tamper, cross-project state and unknown partial state;
- run focused tests, Windows full regression, compileall and hosted CI;
- close through PR, exact main SHA verification and branch cleanup;
- no package/Tag/Release unless a later exact R2 release decision selects one.

## Bounded Critic Review

- Critical/High findings after design correction: `0 / 0`.
- Corrected atomicity risk: applying the existing in-memory service then saving two files could persist a partial decision. Resolution: prepared transaction plus deterministic explicit recovery under one project-local lock.
- Corrected authority risk: directly exposing `add_human_decision` would bypass exact confirmation. Resolution: the Shell receives only snapshot, prepare, apply and explicit recovery commands.
- Corrected product-boundary risk: accepting a Candidate and locking it in one click would collapse TASK-038 and TASK-037 authority. Resolution: Human decision and LOCK remain separate confirmations.
- Corrected audit-history risk: a summary-only projection hides why a decision is being made. Resolution: user-facing projection includes immutable audit identity, findings, dimensions, Failure Codes and proposals.

## Final Plan

1. implement the durable two-store Application and recovery protocol;
2. run focused persistence/recovery Critic tests and correct concrete findings;
3. integrate exact Audit commands and history into the existing Production Control drawer;
4. run focused plus full regression and hosted CI;
5. record closure, merge through PR, verify exact main SHA and delete the branch;
6. start TASK-027 minimum on its own dedicated branch.

The Owner's post-TASK-036 R2 handoff and instruction to continue authorize this bounded TASK-038 implementation. They do not authorize paid generation, external NLE mutation, physical deletion, direct main push or claims beyond Evidence.
