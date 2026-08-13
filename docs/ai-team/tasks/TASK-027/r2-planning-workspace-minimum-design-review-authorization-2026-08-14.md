# TASK-027 — R2 Planning Workspace Minimum Design, Review and Authorization

- Date: `2026-08-14`
- Starting Source of Truth: `main` at `12aa9a790e9c60705deaa13d0dcaf6b4e919c68c`
- Working branch: `codex/task-027-planning-workspace-minimum`
- Governance route: `OWNER_DIRECTED_R2_PRODUCT_PROMOTION`
- DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
- Decision: `IMPLEMENTATION_AUTHORIZED`

## Current audit and Registry check

TASK-037 and TASK-038 are formally complete. TASK-038 implementation PR #26 and closure PR #27 each passed `9 / 9`; exact closure main is `12aa9a790e9c60705deaa13d0dcaf6b4e919c68c`. Stable Product release remains `v0.20.1`; no R2 checkpoint Tag/Release is selected. Existing untracked raw native Evidence remains preserved and excluded.

The Owner-routed R2 order now activates TASK-027 Planning Workspace minimum / Scene Contract.

## Existing Foundation audit

TASK-027 is not greenfield. Current main already contains:

- deterministic Creation Intent and immutable Proposal revisions;
- validated Production Blueprint / Scene Ledger / Reference Registry;
- Scene coverage, Risk C, camera/reference and audio constraints;
- Planning Workspace projection with changed-section comparison;
- exact one-shot Human GO and immutable Approved Production Plan;
- crash-safe checksummed Proposal persistence with CAS;
- Approved Plan -> Blueprint -> Scene -> TASK-037 Slot compilation and exact trace validation;
- Planning/Production bundle and Budget safety foundations;
- generation admission requiring Plan approval, feasibility, required locked inputs and separate paid authorization.

Focused pre-kickoff validation passed `54 / 54`. Missing Product layers are a project-scoped durable Planning Application, user-facing Scene Contract/Proposal review, persisted Human GO and a separate exact Approved Plan -> Production Control installation action.

## DEV Profile re-evaluation

`DEV-4 PRODUCT ORCHESTRATION CRITICAL` is required because Human GO creates durable Plan authority used by later generation and Production Control. The minimum must never convert Proposal display, an AI suggestion or an old approved revision into current execution authority.

Safety floors:

- latest exact Proposal revision only;
- exact Proposal snapshot, Blueprint, reference bindings, policy and cost ceiling;
- one-shot GO confirmation consumed before current-state revalidation;
- GO does not start Provider execution, paid work, Resolve mutation or publishing;
- Approved Plan -> Slot installation is a second one-shot confirmation and one atomic Production Control save;
- copied/mixed/stale Proposal or Production snapshots fail closed;
- no automatic Budget reservation, generation, Candidate creation, LOCK or Audit decision.

## Allowed Files

- `src/ai_video_production/planning_application.py`
- `src/ai_video_production/planning_workspace.py`
- `src/ai_video_production/production_proposal_store.py` only if local CAS serialization is required
- `src/ai_video_production/desktop_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- focused TASK-027/TASK-037/Desktop Shell tests under `tests/`
- TASK-027 documents and canonical Product state/roadmap/task index
- `CHANGELOG.md` for the required Unreleased entry

Package/version metadata, provider adapters, generation queues, Budget mutation, native NLE projects and raw `evidence/` are outside this unit.

## Builder Design

### Phase A — durable Planning Application

- bind fixed project-owned `production-proposal.json` and the existing TASK-037 `production-control.json` through trusted project root/id configuration;
- reload Proposal and Production snapshots for every command;
- list persisted Proposal IDs and project the selected latest revision/Scene Contracts without host paths or credentials;
- prepare Human GO against exact Proposal snapshot/revision, reference bindings, ceiling and rights acknowledgement;
- consume confirmation before revalidation, apply through the accepted GO service and persist with exact CAS;
- expose an independent install confirmation only for a registered exact Approved Plan;
- install Plan -> Scene -> Slot through the accepted TASK-027/037 installer and TASK-037 Application CAS; replay or changed snapshots fail closed;
- detect an already exact-installed trace after restart instead of duplicating Slot state.

### Phase B — user-facing Planning Workspace minimum

- add `企画` to the unified Desktop Shell rather than creating a separate application;
- show Intent, Proposal revision/history, section changes, provider policy, cost/rights preflight and complete Scene Contract cards;
- show Scene frame range, narrative role, source strategy, generation risk, camera, references and audio intent;
- require explicit reference Asset ID/SHA bindings, cost ceiling, rights acknowledgement and approver identity for GO;
- after GO, expose a separate Plan -> Production Control installation confirmation;
- show that Provider execution, paid execution, Resolve mutation and publishing remain not started.

### Phase C — validation and closure

- test stale/replayed GO, new Proposal after prepare, invalid reference binding, rights/cost failure and persistence restart;
- test stale/replayed install, wrong project, exact Plan trace, already-installed restart and no Provider/NLE side effect;
- run focused tests, Windows full regression, compileall, WSL2 compile and hosted CI;
- close through PR, exact main SHA verification and branch cleanup;
- no package/Tag/Release unless a later exact R2 release decision selects one.

## Bounded Critic Review

- Critical/High findings after design correction: `0 / 0`.
- Corrected authority risk: GO and Slot installation cannot be one click. They are separate exact one-shot confirmations.
- Corrected stale-revision risk: the Application reloads the canonical Proposal snapshot before prepare and apply; a newer revision invalidates the pending confirmation.
- Corrected crash/replay risk: GO changes one CAS snapshot and Plan installation changes one CAS Production snapshot. After uncertain response, exact persisted state is inspected before any retry.
- Corrected scope risk: this minimum promotes persisted Proposal/Scene review and GO; it does not invent an AI proposal provider, start generation or claim the full TASK-027 multi-slice product.

## Final Plan

1. implement the durable Planning Application and focused authority/restart tests;
2. run one bounded Critic pass and correct concrete Critical/High findings;
3. integrate Proposal/Scene/GO/Plan-install commands into the unified Desktop Shell;
4. run focused plus full regression and hosted CI;
5. record the bounded Planning Workspace minimum closure, merge through PR and delete its branch;
6. reevaluate the next R3 unit from current canonical state.

The Owner's R2 continuation authorizes this bounded Product promotion. It does not authorize paid generation, Provider calls, Budget reservation, Resolve/Cubase mutation, physical deletion, direct main push or claims beyond Evidence.
