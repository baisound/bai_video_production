# TASK-106 — Planning Generation Deadlock Recovery

Status: `ACTIVE / ATOMIC_UNIT_A_PR_OPEN / CI_AND_NATIVE_GATES_PENDING`

Governance: `DEV-4 FOUNDATION CRITICAL`

## Authority and responsibility

The Owner authorized this corrective Task on 2026-10-11 after the packaged
V6.1.1 Planning screen reported
`planning_generation_apply: [Errno 36] Resource deadlock avoided` while a
Human-confirmed local Planning Proposal was being created.

TASK-106 owns the bounded diagnosis and repair of the Planning-generation
apply/result boundary and its user-facing Shell state. It does not reopen the
completed TASK-027 or TASK-036 history. Instead it depends on:

- TASK-027 as the canonical Creation Intent / Proposal / Blueprint store and
  compare-and-swap publication boundary;
- TASK-036 as the local Planning-generation facade, trusted Shell bridge and
  V6.1.1 UI composition;
- TASK-102 as the current writer-migration admission guard. This unit must not
  bypass or weaken `PMST-R009`.

Initial Builder start identity:

- base / `origin/main`: `a5caf3668c7e248ac5bb8819279e82c8b3f13778`;
- branch: `codex/task-106-planning-generation-deadlock`;
- worktree: `C:\Users\user\.codex\worktrees\task106-planning-deadlock\bai-video-production`;
- initial dirty state: clean.

Current-main reconciliation identity on 2026-10-11:

- base / HEAD / observed `origin/main`:
  `8d96406f34f0fc0d2c9e84622a5aa5c9f971c422`;
- reconciliation source: merged PR607 folder-chooser repair;
- branch and worktree remain unchanged;
- TASK-106 owned changes were restored after the fast-forward and reconciled
  automatically with the current-main Shell and interaction-test changes;
- PR607 source paths outside this Task's Allowed Files remain unmodified.

## Atomic Unit A contract

Goal: make a Planning-generation lock/storage failure bounded, non-replayed and
public-safe while preserving exact TASK-027 canonical publication.

The implementation must:

1. keep one Human confirmation one-shot and never automatically retry local
   inference after an apply failure;
2. convert an escaping local `OSError` into a typed Product outcome;
3. after such an error, read back the deterministic Proposal identity only:
   - exact committed Proposal -> safely reproject that canonical state;
   - confirmed absence -> return a typed non-retryable Product error;
   - conflicting or unreadable state -> return a distinct typed non-retryable
     Product error;
4. never infer success merely from a lock acquisition/release result;
5. preserve the existing statement that a process crash after inference but
   before publication is not durable exactly-once execution;
6. make the Planning-generation UI single-flight, always clear its busy state,
   reload canonical state after the attempt, and display only public-safe
   Japanese failure/recovery copy;
7. synchronize the header Planning-AI indicator with the same readiness state
   used by the Planning pane;
8. leave Human GO, paid execution, Proposal approval, Asset adoption, Timeline,
   Resolve, Export and publication authority unchanged.

## Allowed Files

The Owner-provided `src/bai_product/...` scope spelling was corrected to the
existing canonical package path `src/ai_video_production/...`; this is a path
correction, not a scope expansion.

- `docs/ai-team/tasks/TASK-106/**`
- `src/ai_video_production/task036_planning_generation_application.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_shell_v611.py`
- `tests/test_task036_planning_generation_application.py`
- `tests/test_task036_v611_interaction_contract.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_trusted_launcher.py`
- `tests/test_task106_planning_generation_windows.py` when a Windows-specific
  focused contract is required.

## Prohibited changes and effects

This Atomic Unit must not modify shared lock helpers, schemas,
`planning_application.py`, `production_proposal_store.py`, or
`task036_trusted_launcher.py` without stopping and obtaining a separately
reviewed scope expansion supported by reproduced evidence.

It also does not authorize:

- Ollama/provider execution, paid execution or network access;
- model/runtime download, install or update;
- native Product launch, Windows build, packaging or installer execution;
- private media, Resolve, Cubase, Export or external account mutation;
- commit, push, PR, merge, Release, Deploy or Production Activation;
- destructive cleanup or reuse of historical QA/Evidence paths.

## Acceptance

- exact committed read-back returns the canonical Proposal without a second
  adapter call;
- absent and unreadable/conflicting read-back states use separate typed errors,
  expose no raw OS error, and are not marked retryable;
- provider/store fault tests leave either one complete Proposal or none, never a
  partial Proposal or duplicate deterministic identity;
- duplicate UI activation starts at most one prepare/apply sequence;
- busy state is cleared in `finally` for success, cancel and failure;
- Planning UI RPC failures show Japanese public-safe copy without method names,
  raw English exceptions, paths or exception details;
- header readiness matches Planning-pane readiness;
- focused application, Shell interaction and relevant trusted-launch tests pass;
- diff/scope check shows only Allowed Files.

## Required independent gates

DEV-4 requires independent Tester and Critic review of the frozen Builder
candidate, followed by a Judge decision. This Builder unit may become
commit-ready but cannot self-accept, publish or close TASK-106.

## Atomic Unit A final decision

On 2026-10-11 the current-main integrated source candidate at
`8d96406f34f0fc0d2c9e84622a5aa5c9f971c422` passed its independent DEV-4
gates:

- Tester: `PASS`, 191 relevant tests passed, Critical/High/Medium/Low
  `0/0/0/0`;
- Critic: `ACCEPT`, Critical/High/Medium/Low `0/0/0/0`;
- Judge: `ACCEPT`, Critical/High/Medium/Low `0/0/0/0`.

Atomic Unit A is source-level accepted and commit-ready. TASK-106 remains
`ACTIVE`. On 2026-10-11 the Owner explicitly approved publication operations
for this accepted source unit. That authority covers an explicit-file commit,
task-branch push and PR creation. It does not authorize merge,
packaged/native Product acceptance, build/package, Release, Deploy or
Production Activation; those remain separate gates.

Publication occurred on the authorized task branch as source commit
`080ca951242aaa313859bd8a209e83f8aec0ecc7`. Pull request
`https://github.com/baisound/bai_video_production/pull/608` is open against
`main`. The PR was mergeable when observed; hosted CI and security checks were
still running. No merge authority has been exercised.
