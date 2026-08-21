# TASK-036 P-UX-2I edit history controls design

Date: `2026-08-21`
Status: `IMPLEMENTED / VERIFIED / COMMIT_READY / DEV-3 HIGH ASSURANCE`
Atomic unit: `P-UX-2I_EDIT_HISTORY_CONTROLS_R0`

## 1. Goal

Connect the existing canonical TASK-044 `MOVE`, `TRIM_START`, `TRIM_END`,
`UNDO` and `REDO` operations to the V6.1.1 Edit screen. The screen must use
the existing append-only Timeline edit history, Product Manifest CAS and
Project command history. JavaScript never owns durable edit state.

This unit does not add an edit kind, change a persisted schema, run a Provider,
touch Audio, invoke Resolve, render, Export, publish, release or install a
runtime.

## 2. Ownership and linearization

- TASK-044 continues to own edit preparation, single-use confirmation,
  Project-save transaction, undo/redo stack and restart read-back.
- TASK-036 only exposes strict Shell methods and V6.1.1 controls.
- Every public call remains inside the existing TASK-036 runtime lease.
- Apply remains the existing TASK-044 linearization point. The UI cannot write
  a Timeline, Manifest or history object directly.

## 3. Read-only history control projection

`Task044TimelineEditApplication.history_control_snapshot()` returns only:

- the current Project-history SHA-256;
- `undo.available` and `redo.available`;
- when available, the exact body-free command kind and target identity.

Availability is true only when the current Project command-history candidate
is a `timeline.*` record and the referenced TASK-044 command still exists in
the bound, checksum-valid edit history. Missing, foreign, discontinuous,
recovery-pending or checksum-invalid sources fail closed.

The NLE snapshot includes this projection as `history_controls`. An unbound
edit application projects both actions unavailable and no fabricated history
hash.

## 4. Mutation schemas

New strict Shell calls are:

- `interactive_timeline_prepare_move` with exact clip ID, desired start frame,
  command ID, expected Project Manifest SHA-256 and base Timeline SHA-256;
- `interactive_timeline_prepare_undo` and
  `interactive_timeline_prepare_redo` with exact command ID, expected Project
  Manifest SHA-256, base Timeline SHA-256 and expected Project-history SHA-256;
- `interactive_timeline_cancel_edit` with one exact confirmation ID.

Unknown keys, booleans in place of strings/integers, empty/overlong/NUL text,
stale Timeline, stale Manifest/history and locked presentation tracks fail
closed. MOVE uses only the existing playhead snap anchor and existing TASK-044
range validation.

UNDO/REDO preparation compares the UI-observed Project-history SHA before
selecting the candidate and again immediately before reserving the pending
confirmation. This prevents a stale screen or a concurrent change in the
prepare window from undoing a newer, unseen operation. TASK-044 still rechecks
the same history coordinate at apply. REDO of a generated-Asset placement
keeps the existing current Production/Asset guard.

Every durable TASK-044 command ID is unique. Application admission rejects a
new command that reuses an existing ID, and every checksum-valid loaded history
with duplicate IDs fails closed before projection or Undo/Redo selection. The
UI issues a timestamp-plus-monotonic-sequence identity for every edit action;
the application uniqueness check remains authoritative across restarts.

All edit preparation confirmations are single-use. Human decline calls the
canonical TASK-044 cancel method, including the pre-existing Trim and Track
controls, so repeated declines cannot exhaust the 256-token bound. Apply and
cancel race through the existing application lock and exactly one wins.

## 5. V6.1.1 interaction

- With exactly one unlocked Clip selected, the inspector shows Move, Trim
  start and Trim end controls. The desired frame is collected as a bounded
  integer and the exact prepared command is shown in a second Human confirm.
- Edit menu Undo/Redo buttons are enabled only by the current
  `history_controls` projection.
- `Ctrl+Z` invokes Undo and `Ctrl+Shift+Z` invokes Redo only on the Edit page,
  outside input/textarea/select/contenteditable controls.
- Successful apply refreshes the canonical Timeline snapshot. Decline cancels
  without mutation. No optimistic durable state is retained in JavaScript.

## 6. Allowed scope

May modify:

- `interactive_timeline_application.py`
- `task044_nle_shell.py`
- `task036_shell_ui.py`
- `task036_shell_v611.py`
- direct TASK-044 Shell/history and TASK-036 V6.1.1 tests
- this design document

Must not modify `CHANGELOG.md`, Audio source/schema, Provider adapters,
Resolve/Export, release files, or user-owned `tmp/`.

## 7. Verification

Required evidence:

- history projection empty/undo/redo and stale-history rejection;
- MOVE prepare/apply/reopen and invalid range/stale/locked negatives;
- Undo/Redo strict schema, single-use apply/cancel and current Project-history
  binding;
- placement REDO retains its existing guard;
- old bridge after runtime close has no effect;
- V6.1.1 menu, inspector controls, shortcuts and decline-cancel wiring;
- focused TASK-044/TASK-036 tests, impacted regression, Python compilation,
  embedded JavaScript syntax and `git diff --check`.

## 8. Completion boundary

The unit is complete when a user can move/trim one selected Clip and undo or
redo the current TASK-044 edit from the V6.1.1 screen, with an explicit Human
confirmation and exact canonical read-back after apply or restart. This is a
bounded Edit-screen improvement, not complete model-to-export Product closure.

## 9. Implementation evidence

The implementation was rebased by normal fast-forward integration onto fresh
`origin/main` `b130c77` without an overlapping source path. The final tracked
scope is the four authorized source files, four direct test files and this
design document. `CHANGELOG.md`, Audio, Provider, Resolve/Export, release files
and user-owned `tmp/` were not changed by this unit.

Observed verification:

- direct TASK-044 and V6.1.1 interaction/visual tests: `91 passed`;
- impacted TASK-036/TASK-043/TASK-044 regression: `235 passed`;
- Element/UI contract regression: `62 passed`;
- preliminary full repository regression: `3239 passed, 2 skipped`;
- final fresh-main direct regression, including history-drift, duplicate-ID and
  same-kind cross-store substitution negatives: `94 passed`;
- final fresh-main full repository regression: `3267 passed, 2 skipped`;
- changed Python compilation, embedded V6.1.1 JavaScript syntax and
  `git diff --check`: `PASS`.

The two skips are the existing platform-conditional TASK-014 Windows-drive
locality and TASK-047 Windows-only Inno Setup cases. They are not converted to
PASS and are unrelated to this unit. No Provider, native application, install,
render, Export, publication or release side effect was executed.

The first independent review found two bounded defects: history drift between
Undo/Redo candidate selection and pending reservation, and ambiguous resolution
of duplicate durable command IDs. Both were fixed in the final bytes. Direct
tests now cover the prepare-window drift, runtime ID reuse, checksum-valid
persisted duplicate history and strict Shell rejection.

The second independent review found that a checksum-valid Project history
could substitute another existing same-kind command ID. A common cross-store
validator now requires every `timeline.*` Project record to correspond in
order to one TASK-044 revision. APPLY binds the exact command ID and kind;
UNDO/REDO bind the exact inverse/replay semantics of that APPLY. Snapshot,
prepare and apply all run this validation. The checksum-valid same-kind target
substitution negative fails before pending reservation or mutation.
