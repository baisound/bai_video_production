# TASK-111 — Immutable Audit Input Shell Bridge

Status: `ACTIVE / DEV-4_ACCEPTED / COMMIT_READY`

Governance: `DEV-4 FOUNDATION CRITICAL`

## Authority and responsibility

The ordinary V6.1.1 Asset Review screen could display and apply a Human
Candidate decision only after an immutable TASK-038 Audit already existed.
For a newly adopted `READY_FOR_AUDIT` Candidate with zero Audits, the screen
reported that Audit input was not connected and offered no bounded path to
create the required record.

On 2026-10-12 the Owner explicitly authorized a new TASK-111 allocation,
Shell and dedicated controller changes, related tests and Task documents,
independent DEV-4 validation, commit/push and a Japanese pull request.

TASK-111 owns only the Human-operated Shell bridge that prepares and records
one initial immutable Audit. TASK-038 retains the canonical Audit model,
snapshot stores, Candidate/Asset binding, Human Candidate decision and
recovery ownership. TASK-013 retains structured Visual Compliance evaluation
and its `record_visual_compliance` adapter. TASK-111 does not reopen or modify
TASK-038 history.

## Start identity and overlap decision

- base / HEAD / fetched `origin/main`:
  `8063f8037d3757efa4086af929283c91818696bf`;
- branch: `codex/task-111-audit-input-bridge`;
- worktree:
  `C:\Users\user\.codex\worktrees\task111-audit-bridge\bai-video-production`;
- initial dirty state: clean;
- TASK-036 exact-eight reconciliation was already merged at this base;
- TASK-038 remains historical and unchanged;
- later R24-S3, TASK-101/TASK-109 and packaged-native work remain serialized
  behind this source unit and are not modified here.

## Atomic Unit A contract

Goal: let a Human operator enter and explicitly confirm the first immutable
Audit for one exact `READY_FOR_AUDIT` Candidate without creating another
store or granting Candidate-decision authority.

The implementation must:

1. bind input to exact Candidate ID, Asset ID, Asset SHA-256 and current
   Production/Audit snapshot hashes;
2. fix `auditor_kind` to `HUMAN` and validate structured contract refs,
   scores, findings, failure codes and alternate-use proposals;
3. require a separate one-shot explicit Human confirmation before writing;
4. delegate the canonical write only to
   `Task038AuditApplication.record_audit`;
5. verify the saved immutable record by canonical readback;
6. consume confirmation on apply or cancel and reject double submission;
7. fail closed on stale snapshots, wrong Candidate/Asset, recovery-required
   state, an existing Audit and save failure;
8. expose public-safe errors without echoing submitted values or paths;
9. bound item counts and serialized record size, and reject any input whose
   complete prospective TASK-038 snapshot would exceed its 8 MiB read limit;
10. preserve existing TASK-013 `record_visual_compliance` and TASK-038 Human
   Candidate-decision/recovery behavior;
11. perform no automatic ACCEPT, REJECT, LOCK, regeneration or Provider work.

## Allowed Files

- `docs/ai-team/tasks/TASK-111/**`
- `src/ai_video_production/task111_audit_input_controller.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_shell_v611.py`
- `tests/test_task111_audit_input_controller.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_v611_interaction_contract.py`

## Prohibited changes and effects

- no TASK-038 model/store/schema/history modification;
- no new canonical Audit store;
- no automatic Human Candidate decision or Production LOCK;
- no Provider/inference/model download, billing, generation or regeneration;
- no private media/audio access or persistence;
- no build/package/installer or native Product launch;
- no Resolve, REAPER, Cubase, Release, Deploy or Production Activation;
- no destructive cleanup or foreign worktree/Evidence mutation.

## Acceptance

- a zero-Audit `READY_FOR_AUDIT` Candidate exposes an Audit-input action;
- prepare is effect-zero and returns an exact record digest for confirmation;
- apply requires the literal explicit-Human-confirmation flag and persists one
  TASK-038 Audit through the existing application;
- save/reopen shows exactly that Audit while Candidate lifecycle remains
  `READY_FOR_AUDIT` and no Human Candidate decision exists;
- cancel, invalid JSON, invalid fields, wrong identity, stale snapshots,
  recovery-required state, second Audit, double apply and save failure are
  fail-closed;
- malformed, non-finite, unbounded and prospective-oversize input is rejected
  before confirmation/write, with the existing canonical file unchanged and
  reopenable;
- existing Human decision/recovery and structured Visual Compliance tests pass;
- independent DEV-4 Critic and Tester report zero unresolved Critical/High;
- diff/scope contains only Allowed Files and required Evidence is persisted
  and read back outside the worktree before completion.

## Current result and next action

Atomic Unit A implementation and its single bounded Critic repair cycle are
validated. The initial independent Critic found one High, one Medium and two
Low findings: prospective store oversize, raw backend error display, missing
bridge-contract declarations and eager prompts after cancel/invalid input.
All four are fixed with regression coverage. Corrected-candidate Critic,
Tester and Judge each returned `ACCEPT`, with unresolved/new
`Critical/High/Medium/Low = 0/0/0/0`.

Builder verification is focused `129 PASS`, related Audit/Visual Compliance
`163 PASS` and integration `120 PASS`. Independent Tester verification is
dedicated `129 PASS`, extended TASK-038/TASK-013 `169 PASS`, integration
`120 PASS`, plus direct recovery/stale/cancel/no-write probes. Compileall,
diff and Allowed Files checks pass. The external Evidence run identity is
`TASK-111/atomic-unit-a/20261012-r01`; commit/push and the authorized Japanese
PR are next. No build, native Product, Provider or release effect is included.
