# TASK-108 — Central AI Model Save Handler Runtime Corrective

Status: `ACTIVE / IMPLEMENTATION_VALIDATED / PR_PENDING`

Governance: `DEV-2 STANDARD`

## Authority and responsibility

During the authorized TASK-106 packaged-native F0-F10 acceptance on
2026-10-11, the Owner confirmed that the TASK-107 Settings layout repair made
the central AI-model save control reachable, but selecting
`AIモデル設定を保存` produced no visible response.

This is a new runtime save-handler and test-coverage responsibility. It does
not reopen the TASK-106 Planning deadlock repair or the TASK-107 Settings
reachability repair. TASK-108 depends on both merged changes and owns only the
bounded correction needed to make the existing central AI-model selection save
path execute and report its existing Product result.

## Start identity and overlap decision

- base / HEAD / observed `origin/main`:
  `23b38a3d7240e2155c6b9ba2886c0980b71d98fc`;
- branch: `codex/task-108-ai-model-save-handler`;
- worktree:
  `C:\Users\user\.codex\worktrees\task108-settings-save\bai-video-production`;
- initial dirty state: clean;
- TASK-106 merge `79701a2e` and TASK-107 merge
  `3ba0ee5b807774f0f233751532d04f6825ecd7eb` are ancestors of the base;
- the active TASK-106 native-QA worktree is preserved and must not be modified,
  cleaned or reused by this Task;
- historical dirty TASK-036 worktrees that also touch the Shell remain foreign
  and must not be overwritten or used as a base.

## Root cause

`renderCentralModelSettings()` creates the existing save button. For every
central-model workload, its click handler calls `q(selector, root)`, but the
production Shell defines only `$` and `qa`. With a non-empty workload the
undefined identifier throws a JavaScript `ReferenceError` before
`connection_settings_update` reaches the existing `call()` boundary. As a
result, no settings mutation occurs and no public-safe toast is shown.

The current interaction harness defines a test-only `q()` stub and therefore
masks the missing production helper. Its save case also does not drive a
non-empty workload through the real selector path.

## Atomic Unit A contract

Goal: restore the existing central AI-model save path with the smallest
production-safe selector correction and a regression test that cannot pass by
inventing helpers absent from the shipped Shell.

The implementation must:

1. use an existing production DOM selection primitive or a direct bounded
   `querySelector` rooted at `settingsContent`;
2. preserve the existing `connection_settings_update` payload, revision/CAS
   behavior, busy state, post-save refresh and Japanese public-safe messages;
3. preserve TASK-106 Planning recovery/header synchronization and TASK-107
   Settings scrolling unchanged;
4. add a non-empty-workload interaction regression that uses the shipped
   selector semantics, reaches exactly one update RPC and verifies the chosen
   route identity;
5. remove the test-only masking of an undefined production helper;
6. execute no Provider, inference, model download, paid operation or native
   side effect.

## Allowed Files

- `docs/ai-team/tasks/TASK-108/**`
- `src/ai_video_production/task036_shell_v611.py`
- `tests/test_task036_v611_interaction_contract.py`

## Prohibited changes and effects

- no connection-settings schema/store/bridge or Catalog behavior change;
- no Planning application, proposal, lock, provider or retry change;
- no modal layout/CSS change owned by TASK-107;
- no shared helper expansion unless the focused regression proves it is needed;
- no native Product launch, build/package/installer, provider call, paid
  execution, model/runtime download, private media, Resolve, Release, Deploy or
  Production Activation;
- no commit, push, PR or merge without a later explicit publication gate;
- no mutation or cleanup of TASK-106 QA artifacts or foreign dirty worktrees.

## Acceptance

- a non-empty central-model workload can save one selected route without a
  JavaScript exception;
- exactly one `connection_settings_update` RPC receives the existing complete
  workload-mode map and the selected central route;
- save busy state always clears and the existing model view is re-rendered;
- success retains the existing no-execution/no-billing Japanese notification;
- RPC failure retains the existing public-safe message and performs no retry;
- TASK-106 Planning and TASK-107 visual/interaction focused regressions pass;
- diff/scope review contains only Allowed Files;
- independent Tester responsibility is required before source acceptance.

## Current checkpoint

Atomic Unit A replaces the undefined test-only `q(...)` dependency with a
bounded `host.querySelector(...)` call rooted at `settingsContent`. The new
non-empty-workload interaction regression executes the shipped function without
defining `q`, selects `plan-local`, and verifies exactly one existing
`connection_settings_update` RPC with the complete workload-mode map, selected
route identity, busy-state release, refresh and public-safe success message.

The focused red case reproduced `ReferenceError: q is not defined`; the fixed
case passed, and the final TASK-106/TASK-107/TASK-108 related regression is
`170 PASS`. No Provider, inference, download, paid or native Product effect was
performed. Detailed validation is recorded in
`evidence/atomic-unit-a-implementation-validation-20261011.md`.

## Next action

Commit and publish the bounded candidate through an Owner-authorized pull
request. A replacement Windows package/native confirmation remains a separate
later gate and is not implied by source-level acceptance.
