# TASK-036 P-UX-2D5 Final Review Export Queue Handoff

Date: 2026-08-21
Atomic unit: `P-UX-2D5_FINAL_REVIEW_EXPORT_QUEUE_R0`
Execution owner: Development 2, by explicit Owner handoff
Development depth: `DEV-4 FOUNDATION CRITICAL`

## Authority and integration state

This unit continues the reserved P-UX-2D5 boundary after P-UX-2D1 through D4.
It was completed in the persistent TASK-036 worktree on
`codex/task-036-pux2d5-final-review-export-queue`. Current `origin/main`
`e394cead16407d7177419a07a687094350f3b017` was integrated by the normal merge
commit `1c5a39efa2da0f4563c522f629d8c86355a3196e`; no rebase, force push or reset was
used. The additive TASK-049 Game Intelligence UI and the D4/D5 Final Review flow
are both preserved.

The unit may compile one private `ExportPreparation` from the current typed
Final Review approval and enqueue exactly one logical TASK-044 Export Job after
explicit Human confirmation. It grants no dispatch, render, publication,
native execution, release, deployment or Production authority. It does not mint
an Audio completion receipt or a P-UX-2E completion marker.

## Design and implementation

### Durable admission and Project boundary

- TASK-044 admits `final_approval` as an exclusive input binding under the
  canonical Project lock. The same operation is idempotent; a different
  operation or legacy multiple match fails closed.
- Canonical query and restart recovery validate the expected Project against
  both the current Manifest and Job collection while holding the same lock.
  Valid-checksum Manifest and Job swaps from another Project are rejected.
- Missing stores remain read-only. Valid and dangling store symlinks are
  rejected before existence checks.
- Startup recovery is explicit and EXPORT-scoped. Interrupted EXPORT Jobs move
  once to `UNKNOWN`; unrelated local Job kinds remain unchanged.

### Final Review application and Shell

- The private preparation provider is evaluated only for a current typed
  approval. Stale or restarted projections read only canonical durable Job
  truth and never regenerate provider data.
- Prepare/apply binds the exact Project, Manifest, Timeline, readiness,
  approval, preset and logical destination coordinates. Confirmation tokens
  are single-use, bounded and concurrency-safe.
- Distinct confirmations and preparations for the same approval still produce
  exactly one durable Job. Cancel and state projection preserve durable
  state/version truth.
- The Shell binds D1/D4/D5 through TASK-044, exposes no host path and does not
  start a side effect. Normal trusted launch leaves the private provider
  unbound.
- UI contracts keep TASK-049 additive controls and exactly one listener for
  each merged interaction.

### Runtime ownership and recovery

The trusted launcher holds one nonblocking OS-backed Project runtime lease for
the mutation-capable composition. Every public TASK-044 timeline/edit/export
and D5 operation is guarded for its full duration. Close rejects new work,
waits for admitted work, releases the OS lock only afterward, and supports
parallel close, GC, lazy construction and nested operations without deadlock.
Self-close during an operation fails closed and remains retryable. A second
live launcher cannot recover or mutate the first launcher's Jobs.

## Critic and remediation

DEV-4 review found and closed the following material issues:

- post-enqueue readiness initially projected the scoped Job as unscoped;
- multiple pending confirmations could enqueue multiple Jobs for one approval;
- direct store projection trusted incomplete Project coordinates;
- restart recovery could affect live or non-EXPORT Jobs;
- a released launcher could leave a cached mutation bridge usable;
- close and mutation had operation-lifetime and lazy-factory race windows;
- an Application created for one Project could accept a later checksum-valid
  Manifest plus Job collection swap from another Project.

Each issue received negative, concurrency, restart or bound Shell coverage.
Independent Critic and final Judge/Acceptance both report `PASS` with residual
`C/H/M/L = 0/0/0/0`.

## Verification evidence

- Focused D5/TASK-043/TASK-044/Shell/UI regression: `164 passed`.
- Final locally collectible repository regression: `2234 passed, 1 skipped`.
  The skip is the Windows-only Inno Setup acceptance.
- `compileall` for `src` and `tests`: PASS.
- Embedded V6.1.1 JavaScript `node --check`: PASS.
- `git diff --check`: PASS.

The complete repository suite is `NOT_CONFIRMED` in the WSL environment because
`tests/test_task049_dbd_training_studio_packaging.py` and
`tests/test_task050_r7_structured_ui_errors.py` require Windows `tkinter` and
were excluded from the locally collectible run. Hosted Windows checks are the
required confirmation for those tests. No paid, native, external, release or
Production side effect was performed by this verification.

## Shared-write and remaining gates

`CHANGELOG.md` is intentionally unchanged because the required shared
Integration Lock was not available. That update remains parked; it must not be
manufactured or bypassed for this unit.

Remaining Human/Owner gates include current external Gate receipts, Final
Review approval, the D5 Queue-add confirmation, each TASK-044 dispatch/render
confirmation, P-UX-2E packaged Windows output and QA read-back, and all
Release/Deploy/Production actions. Draft PR publication does not satisfy or
expand any of those gates.
