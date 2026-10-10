# TASK-036 P-UX-2E Native Folder Chooser Repair Evidence

Date: `2026-10-11`

Status: `SOURCE_REPAIR_PASS / PACKAGED_ACCEPTANCE_PENDING`

## Scope and authority

- Active Product: BAI VIDEO PRODUCTION
- Active Task: `TASK-036 / P-UX-2E`
- Atomic Unit: Windows native folder chooser repair
- Governance depth: `DEV-3`
- Base commit: `a5caf3668c7e248ac5bb8819279e82c8b3f13778`
- Branch: `codex/task-036-folder-chooser-repair-20261011`
- Authorized effects: bounded source, test, native selection-only diagnostic, and Evidence updates
- Prohibited effects preserved: package build, Product launch, Provider or paid execution, media ingest, project mutation, Resolve/Cubase mutation, export, Release, Deploy, and Production

## Observed failure and root cause

Packaged manual QA established a differential result: the native media file picker opened normally, while Project and EDITOR_WORK directory pickers failed before displaying a dialog. A source-level native diagnostic reproduced the underlying `FolderBrowserDialog` failure under an isolated profile: the default Desktop root could not be retrieved.

The three directory picker scripts did not set `FolderBrowserDialog.RootFolder`. This left the control dependent on the profile's Desktop shell root, which is not available in the isolated packaged-acceptance profile.

## Repair

- Set `FolderBrowserDialog.RootFolder` to `System.Environment.SpecialFolder.MyComputer` for Project, EDITOR_WORK, and FasterWhisper model directory selection.
- Retained the fixed, non-interpolated PowerShell scripts, temporary topmost owner, existing-path validation, selection-only behavior, and cancellation semantics.
- Added bounded Japanese public errors for folder selection and media ingest. Raw bridge method names and private exception messages are no longer the default user-facing result for these routes.
- Added contract coverage for all three profile-independent folder roots and both public error bindings.

## Verification

| Check | Result |
| --- | --- |
| Diff whitespace check | `PASS` |
| Focused dialog and interaction contracts | `32 PASS` |
| Dialog, interaction, and Shell UI regression | `90 PASS` |
| Real Windows Project-folder dialog from current source | `PASS` — dialog opened; Human selected Cancel; Python result was `None` |
| Project/media/folder mutation during native diagnostic | `NONE` |

The first expanded regression attempt passed 85 tests but could not set up five `tmp_path` cases because the host's shared pytest temporary directory was inaccessible. The same exact test set was rerun with a unique operation-owned directory under the OS temporary root and passed `90 / 90`. That temporary test directory was identity-checked and removed after the run.

## Placement and residuals

- All source and test changes are inside the dedicated TASK-036 worktree.
- The native diagnostic used the existing operation-owned contained run root `.runtime/t36-folder-diagnostic/20261011-r01` in that worktree.
- The diagnostic run root is intentionally preserved until external Evidence read-back and handoff are complete.
- No task-owned path was created at a drive root or directly beneath a drive root.

## Decision

The bounded source repair is `PASS` and commit-ready. The previously built EXE does not contain this change and remains unsuitable for closing P-UX-2E. A fresh package build and packaged native acceptance require their own explicit Human authority. TASK-036 remains open and no completion token is minted.
