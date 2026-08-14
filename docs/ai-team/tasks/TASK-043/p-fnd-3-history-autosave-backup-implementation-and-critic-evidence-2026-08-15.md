# TASK-043 P-FND-3 History / Autosave / Backup — Implementation and Critic Evidence

- Date: `2026-08-15`
- Base: `main@3ba4df947ab2939ef7daed030a3ee69a3c31f07a`
- Branch: `refactor/task-043-history-autosave-backup`
- Authority: `AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`

## Implemented contract

- closed `project-command-history.schema.json` in public and packaged resources;
- append-only APPLY/UNDO/REDO records, where Undo and Redo are new compensating
  commands rather than deletion or mutation of historical Evidence;
- exact Manifest checksum/revision chain, bounded records, explicit STALE targets
  and CAS-protected `history.json`;
- no command payload, private Prompt body, credential, external replay authority
  or Evidence-deletion authority in history;
- bounded Autosave debounce/quiescence policy using the accepted coordinated save
  transaction, followed by bounded Manifest checkpoint retention;
- checksum-bound, contained and size-bounded Project Backup creation/rotation;
- read-only restore preview and restore as a new exact-CAS Project revision;
- restore conflict or child-binding-set change becomes Human review instead of an
  ambiguous/destructive overwrite.

## Critic review and corrections

1. `HIGH / CLOSED` — Backup metadata originally lacked an exact field/authority
   check. Parsing now requires the closed field set, version, Project identity,
   UTC timestamp and authority constants before trusting the snapshot.
2. `HIGH / CLOSED` — A tampered Backup child could be oversized or resolve outside
   the snapshot through a filesystem redirection. Verification now enforces exact
   containment, regular non-symlink files, per-child/total size bounds and binding
   checksums before preview or restore.
3. `HIGH / CLOSED` — Restore could silently add/remove bindings. Automated restore
   requires the exact current binding identity set; any set change is a typed Human
   review gate.
4. `HIGH / CLOSED` — Autosave could become a second ungoverned write path. It calls
   `ProductProjectSaveCoordinator` with the exact prior Manifest checksum and does
   not duplicate child bytes into the Autosave checkpoint.
5. `MEDIUM / CLOSED` — History revision booleans could pass Python integer checks.
   The record contract now rejects bool and requires exact integer +1 progression.
6. `MEDIUM / CLOSED` — Redo after a new branch could resurrect stale work. Replay
   reconstruction clears only the redo candidate stack while retaining every
   historical record; the new branch cannot call Redo.

Final unresolved Critical/High: `0 / 0`.

## Validation

- `python -m compileall -q src tests`: PASS
- TASK-043 focused: `55 passed`
- full Windows Python 3.12 regression: `1042 passed, 1 skipped`
- packaged/public command-history schema bytes: exact
- schema meta-validation and representative instance validation: PASS
- `git diff --check`: required before commit

The one skip is the existing `tests/test_task034_credential_vault.py` non-Windows
contract and is unrelated to P-FND-3.

## Boundaries and next gate

No Provider, paid, credential, media-generation, Resolve, Cubase, native project,
package-version, Tag, Release or Deploy operation occurred. P-FND-3 is a foundation
checkpoint and does not justify a standalone release. Hosted CI must pass before
main merge. After exact merge/cleanup, P-FND-4 durable Product jobs / Export Queue
foundation is the next authorized unit.
