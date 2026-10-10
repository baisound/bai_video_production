# TASK-108 Intake and Root-Cause Evidence — 2026-10-11

Result: `PASS / TASK ALLOCATED / IMPLEMENTATION NOT STARTED`

- Active Project: BAI VIDEO PRODUCTION
- Task: TASK-108
- Atomic Unit: central AI-model save-handler runtime corrective
- Base / HEAD / observed `origin/main`:
  `23b38a3d7240e2155c6b9ba2886c0980b71d98fc`
- Worktree:
  `C:\Users\user\.codex\worktrees\task108-settings-save\bai-video-production`
- Branch: `codex/task-108-ai-model-save-handler`
- Initial dirty state: clean before this Task record was created.

## Native finding

The TASK-106 integrated package executable had SHA-256
`66f2ad5ec302bcca8ae5fc7c641901668e6bee281d034266ac457cf7693a7225`.
The Owner observed that the central AI-model save control was reachable after
TASK-107 but produced no visible response when selected. No Provider execution
or model download was authorized or performed.

## Source proof

- Production Shell defines `$` and `qa`, not `q`.
- The save handler calls `q(...)` for every included central workload.
- That exception occurs before the existing `call('connection_settings_update',
  ...)` boundary, explaining both the absent mutation and absent public error
  toast.
- The interaction harness defines its own `q()` stub, so it can execute a
  function shape that is not present in the shipped Shell.
- TASK-108 was absent from the canonical task directory before allocation;
  TASK-105 through TASK-107 were already allocated.

## Scope and overlap result

- Minimum source scope: `task036_shell_v611.py`.
- Minimum regression scope: `test_task036_v611_interaction_contract.py`.
- TASK-106 native-QA artifacts and documentation remain owned by TASK-106.
- TASK-107 is merged and its dedicated worktree is clean.
- Foreign historical TASK-036 worktrees with dirty overlapping Shell/test
  files remain untouched.
- No source, test, provider, build, package, native, commit, push or external
  Product effect was performed in this intake unit.

## Next action

Implement one bounded selector correction and the non-empty-workload
regression under the TASK-108 Allowed Files, then run focused DEV-2 validation
and independent Tester review. Publication and any replacement native package
remain later explicit gates.

