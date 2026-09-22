# TASK-036 P-UX-2E Export Journey Implementation Evidence

Date: `2026-09-22`

## Identity and scope

- Active Project: `BAI VIDEO PRODUCTION`
- Active Task: `TASK-036 / P-UX-2E`
- Atomic Unit: `P-UX-2E-EXPORT-JOURNEY-R0`
- DEV profile: `DEV-4 FOUNDATION CRITICAL`
- Worktree: `C:\Users\user\.codex\worktrees\130a\bai-video-production`
- Branch: `codex/task-036-pux2e-export-journey`
- Base and pre-commit HEAD: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Current `origin/main` at bind time: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Final implementation commit: this Evidence is included in that commit; its exact
  SHA is persisted in the external checkpoint after commit.

This unit is a bounded continuation of the existing TASK-036 P-UX-2E
responsibility. It does not allocate a new Task and does not change the
Asset, Timeline, Final Review or Export Queue ownership boundaries.

## Concurrency and Allowed Files

`docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json` revision `143` was read from
the bound main snapshot. Its eight recorded locks are all closed/released;
nonclosed lock count is `0`.

The fresh open-PR audit found four open PRs. PR `#562` also changes
`src/ai_video_production/task036_shell_ui.py`, but its changes are confined to
the TASK-098 managed-transcription composition. This unit adds only the
separate Export Queue bridge methods in that file. No same-symbol overlap was
found. The remaining open PRs do not touch this unit's implementation or test
paths.

Exact changed-file ownership for this unit:

- `src/ai_video_production/export_queue_application.py`
- `src/ai_video_production/task044_nle_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_shell_v611.py`
- `tests/test_task044_export_queue.py`
- `tests/test_task036_pux2e_export_dispatch.py`
- `tests/test_task044_nle_shell_ui.py`
- `tests/test_task036_v611_interaction_contract.py`
- `tests/test_task036_v611_visual_contract.py`
- this Evidence document

No shared lock registry, current-state file, roadmap, packaging spec or
unrelated Product path is modified.

## Implemented user journey

The existing V6.1.1 visual language is preserved and the Export page now
projects one explicit seven-step journey:

1. Project / Asset selection;
2. edit inspection;
3. Final Review and Human approval;
4. preset and destination settings read-back;
5. preflight;
6. individually confirmed Export dispatch and canonical progress polling;
7. success result and explicit destination-open action.

The page gives direct, Japanese-labelled navigation to the edit and Final
Review screens. It renders the existing durable TASK-044 Queue states without
creating a browser-side store, Timeline or Export engine. `DISPATCHING` and
`RUNNING` are polled by bounded timeout refresh against the canonical Queue.

Recoverable `HUMAN_REQUIRED` jobs may re-run only the existing
`RESUME_PREFLIGHT` transition on the same Job. This route never dispatches or
automatically replays the Export. `FAILED` returns the operator to review;
`UNKNOWN` remains reconciliation-only and is never retried automatically.

A successful Job can open its private destination only through the trusted
host bridge. The browser cannot submit, persist or receive a host path. The
bridge requires the same canonical Job to be `SUCCEEDED`, re-derives the
private destination, requires an absolute existing non-reparse directory and
then invokes the injected/native opener. Result projection retains
`host_output_path_exposed: false`.

## Verification

Final focused Windows run, using the task-owned basetemp
`C:\Users\user\AppData\Local\Temp\bvp-task036-pux2e-20260922-win-r3\pytest`:

```text
110 passed in 7.01s
```

Final adjacent Windows Final Review, Shell, Export Queue, packaging and
P0E native-QA contract run, using
`C:\Users\user\AppData\Local\Temp\bvp-task036-pux2e-20260922-win-r6\pytest`:

```text
275 passed in 36.86s
```

Additional checks:

- `python -m compileall -q src/ai_video_production`: `PASS`
- `git diff --check`: `PASS`
- Node-backed UI-state projections cover no Project, edit, approval,
  settings, queued, ready, running, succeeded, Human-required, failed and
  unknown states: included in the passing focused run.
- Existing WSL adjacent attempt: `160 PASS / 2 Windows-only skips / 3
  Windows-PowerShell execution errors`; the affected packaging/native-QA set
  was rerun on Windows and passed, then included again in the final `275`
  passing run.
- A Windows rerun against the default shared pytest temp root produced `79
  PASS / 31 setup errors` because that foreign root denied directory listing.
  It was not reused or repaired. A first isolated rerun found one invalid new
  test fixture (`109 PASS / 1 FAIL`); the fixture was corrected and the exact
  focused suite passed as recorded above.

## UI and packaged/native read-back

The exact updated HTML was served on loopback only and inspected through the
Computer Use browser at a `1280 x 720` viewport. The seven steps, current-step
highlight, top actions, setting area and Queue area were visually present and
readable in one screen. `編集内容を確認` navigated to the Edit page and
`最終確認へ進む` navigated to Final Review. The preview process was terminated
after inspection.

This is source-UI visual Evidence, not packaged-native Evidence. No current
`builds\BAI Video Production\BAI Video Production.exe` exists in this
worktree. The canonical spec also requires same-build TASK-048 Controller /
worker inputs and a TASK-059 helper identity. This unit did not synthesize,
download or substitute those dependencies. Therefore:

- source UI read-back: `PASS`
- Windows packaging/native-QA contracts: `PASS`
- rebuilt packaged EXE launch and interaction: `NOT_CONFIRMED`
- exact exported media bytes/hash/properties: `NOT_CONFIRMED`
- `TASK036_MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_COMPLETE`: **not minted**

## Output roots, residuals and effects

All test/build-like output used a contained task-owned root; no task artifact
was created at a drive root or directly beneath a drive root.

Intentional residuals retained for review/reproduction:

- `/tmp/bvp-task036-pux2e-20260922-r1/` — WSL validation venv;
- `C:\Users\user\AppData\Local\Temp\bvp-task036-pux2e-20260922-win-r1\`
  — Windows validation venv, including the preserved failed initial venv and
  working `venv313`;
- `C:\Users\user\AppData\Local\Temp\bvp-task036-pux2e-20260922-win-r2\`
  through `...-win-r6\` — isolated pytest basetemps;
- `C:\Users\user\.codex\visualizations\2026\09\22\01a0c6ce-da17-7221-9506-3dd7b45b7d09\task036_export_journey_preview.py`
  — read-only loopback preview helper outside the repository.

No Provider execution, model/runtime acquisition, Owner Voice or other voice
operation, private-media access, Resolve mutation, Release, Deploy or
Production Activation occurred. No Product Export was dispatched during this
unit.

## Result and next action

Result: `IMPLEMENTED_LOCAL / TESTED / COMMIT_AND_PR_READY`.

The next action is review and PR publication of the exact commit. A later
P-UX-2E native gate must use the canonical same-build dependencies and an
authorized synthetic/offline fixture to close the remaining packaged EXE and
output-byte read-back requirements.
